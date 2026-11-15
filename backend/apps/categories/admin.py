from django.contrib import admin
from apps.categories.models import Category, WorkerCategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "display_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(WorkerCategory)
class WorkerCategoryAdmin(admin.ModelAdmin):
    list_display = ("worker", "category", "is_primary", "experience_years")
