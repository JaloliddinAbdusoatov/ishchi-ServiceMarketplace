from django.contrib import admin
from apps.profiles.models import EmployerProfile, WorkerPortfolioItem, WorkerProfile


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "location", "district", "is_verified", "verification_status", "rating_avg", "is_available")
    list_filter = ("is_verified", "verification_status", "is_available", "pricing_type")
    search_fields = ("full_name", "location", "district")


@admin.register(WorkerPortfolioItem)
class WorkerPortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "worker", "completed_year", "created_at")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company_name", "employer_type", "location", "rating_avg")
    list_filter = ("employer_type",)
    search_fields = ("full_name", "company_name", "location")
