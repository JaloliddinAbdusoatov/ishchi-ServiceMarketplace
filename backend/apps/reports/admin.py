from django.contrib import admin
from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("target_type", "reason", "status", "reporter", "resolved_by", "created_at")
    list_filter = ("status", "target_type", "reason")
