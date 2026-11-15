from django.conf import settings
from django.db import transaction
from apps.categories.models import Category, WorkerCategory
from apps.common.exceptions import BusinessRuleViolation
from apps.profiles.models import WorkerProfile


class CategoryService:
    """Enforces ISHCHI category integrity rules (max 10 per worker, no duplicates, active-only)."""

    @classmethod
    @transaction.atomic
    def update_worker_categories(cls, worker_profile: WorkerProfile, assignments: list[dict]) -> list[WorkerCategory]:
        max_cats = getattr(settings, "MAX_CATEGORIES_PER_WORKER", 10)
        if len(assignments) > max_cats:
            raise BusinessRuleViolation(
                f"A worker can have at most {max_cats} assigned categories.",
                code="max_categories_exceeded",
            )

        seen_ids = set()
        primary_count = 0
        for item in assignments:
            cat_id = str(item["category_id"])
            if cat_id in seen_ids:
                raise BusinessRuleViolation(
                    "Duplicate category assignments are not allowed.",
                    code="duplicate_category_assignment",
                )
            seen_ids.add(cat_id)
            if item.get("is_primary"):
                primary_count += 1

        if primary_count > 1:
            raise BusinessRuleViolation(
                "A worker can have at most one primary category.",
                code="multiple_primary_categories",
            )

        # Lock worker profile row to serialize concurrent category updates
        locked_worker = WorkerProfile.objects.select_for_update().get(pk=worker_profile.pk)

        categories_map = {
            str(c.id): c
            for c in Category.objects.filter(id__in=seen_ids, is_active=True)
        }
        if len(categories_map) != len(seen_ids):
            raise BusinessRuleViolation(
                "One or more selected categories do not exist or are inactive.",
                code="invalid_or_inactive_category",
            )

        WorkerCategory.objects.filter(worker=locked_worker).delete()
        created = []
        for item in assignments:
            wc = WorkerCategory.objects.create(
                worker=locked_worker,
                category=categories_map[str(item["category_id"])],
                is_primary=bool(item.get("is_primary", False)),
                experience_years=item.get("experience_years"),
            )
            created.append(wc)
        return created

    @classmethod
    @transaction.atomic
    def deactivate_category(cls, category: Category) -> Category:
        """
        Deactivates a category and removes any active worker category assignments
        referencing it (business rule: deactivated categories must not remain as active assignments).
        """
        locked_cat = Category.objects.select_for_update().get(pk=category.pk)
        locked_cat.is_active = False
        locked_cat.save(update_fields=["is_active", "updated_at"])
        WorkerCategory.objects.filter(category=locked_cat).delete()
        return locked_cat

    @classmethod
    @transaction.atomic
    def update_category(cls, category: Category, validated_data: dict) -> Category:
        locked_cat = Category.objects.select_for_update().get(pk=category.pk)
        parent = validated_data.get("parent", locked_cat.parent)
        if parent and str(parent.id) == str(locked_cat.id):
            raise BusinessRuleViolation("A category cannot be its own parent.", code="cyclic_category")

        # Prevent cycle in ancestor chain
        ancestor = parent
        while ancestor is not None:
            if str(ancestor.id) == str(locked_cat.id):
                raise BusinessRuleViolation("Circular category hierarchy is not allowed.", code="cyclic_category")
            ancestor = ancestor.parent

        was_active = locked_cat.is_active
        for attr, val in validated_data.items():
            setattr(locked_cat, attr, val)
        locked_cat.save()

        if was_active and not locked_cat.is_active:
            WorkerCategory.objects.filter(category=locked_cat).delete()

        return locked_cat
