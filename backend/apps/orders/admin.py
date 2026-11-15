from django.contrib import admin
from apps.orders.models import OrderImage, ServiceOrder


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "category", "budget", "status", "assigned_worker", "created_at")
    list_filter = ("status", "budget_type", "work_type")
    search_fields = ("title", "location", "district")


@admin.register(OrderImage)
class OrderImageAdmin(admin.ModelAdmin):
    list_display = ("order", "caption", "display_order", "created_at")
