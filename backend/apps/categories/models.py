from django.db import models
from django.db.models import Q
from apps.common.models import TimeStampedUUIDModel
from apps.common.validators import validate_image_file
from apps.profiles.models import WorkerProfile


class Category(TimeStampedUUIDModel):
    """Hierarchical service category taxonomy (parent -> child categories)."""

    parent = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="children",
    )
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=120, db_index=True)
    name_uz = models.CharField(max_length=120, blank=True, default="")
    name_ru = models.CharField(max_length=120, blank=True, default="")
    name_en = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    image = models.ImageField(
        upload_to="categories/",
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = "categories_category"
        ordering = ["display_order", "name"]
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["is_active", "parent"], name="idx_category_active_parent"),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def get_localized_name(self, lang="uz"):
        mapping = {"uz": self.name_uz, "ru": self.name_ru, "en": self.name_en}
        return mapping.get(lang) or self.name


class WorkerCategory(TimeStampedUUIDModel):
    """
    Junction table assigning categories to workers.
    Business rules:
    - Maximum 10 categories per worker.
    - No duplicate (worker, category) assignments.
    - At most 1 primary category per worker.
    - Deactivated categories cannot remain as active worker assignments.
    """

    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="worker_categories",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="worker_assignments",
    )
    is_primary = models.BooleanField(default=False)
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "categories_worker_category"
        ordering = ["-is_primary", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["worker", "category"],
                name="uq_worker_category",
            ),
            models.UniqueConstraint(
                fields=["worker"],
                condition=Q(is_primary=True),
                name="uq_worker_primary_category",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "is_primary"], name="idx_wc_category_primary"),
        ]

    def __str__(self):
        return f"{self.worker.full_name} -> {self.category.name} (primary={self.is_primary})"
