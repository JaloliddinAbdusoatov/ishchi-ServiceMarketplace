from django.contrib import admin
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("order", "direction", "rating", "reviewer", "reviewee", "created_at")
    list_filter = ("direction", "rating")
