from django.contrib import admin
from apps.applications.models import OrderApplication


@admin.register(OrderApplication)
class OrderApplicationAdmin(admin.ModelAdmin):
    list_display = ("order", "worker", "proposed_price", "status", "created_at")
    list_filter = ("status",)
