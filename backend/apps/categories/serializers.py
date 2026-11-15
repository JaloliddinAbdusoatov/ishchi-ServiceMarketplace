from rest_framework import serializers
from apps.categories.models import Category, WorkerCategory


class CategoryChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "slug",
            "name",
            "name_uz",
            "name_ru",
            "name_en",
            "description",
            "image",
            "is_active",
            "display_order",
        ]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        model = Category
        fields = [
            "id",
            "parent",
            "parent_name",
            "slug",
            "name",
            "name_uz",
            "name_ru",
            "name_en",
            "description",
            "image",
            "is_active",
            "display_order",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children(self, obj):
        children_qs = obj.children.filter(is_active=True).order_by("display_order", "name")
        return CategoryChildSerializer(children_qs, many=True, context=self.context).data


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "parent",
            "slug",
            "name",
            "name_uz",
            "name_ru",
            "name_en",
            "description",
            "image",
            "is_active",
            "display_order",
        ]


class WorkerCategoryItemSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    is_primary = serializers.BooleanField(default=False)
    experience_years = serializers.IntegerField(min_value=0, max_value=80, required=False, allow_null=True)


class WorkerCategoriesAssignSerializer(serializers.Serializer):
    categories = WorkerCategoryItemSerializer(many=True)


class WorkerCategoryReadSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField(source="category.id", read_only=True)
    slug = serializers.CharField(source="category.slug", read_only=True)
    name = serializers.CharField(source="category.name", read_only=True)
    name_uz = serializers.CharField(source="category.name_uz", read_only=True)
    name_ru = serializers.CharField(source="category.name_ru", read_only=True)
    name_en = serializers.CharField(source="category.name_en", read_only=True)

    class Meta:
        model = WorkerCategory
        fields = [
            "id",
            "category_id",
            "slug",
            "name",
            "name_uz",
            "name_ru",
            "name_en",
            "is_primary",
            "experience_years",
        ]
