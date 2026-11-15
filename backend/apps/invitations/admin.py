from django.contrib import admin
from apps.invitations.models import OrderInvitation


@admin.register(OrderInvitation)
class OrderInvitationAdmin(admin.ModelAdmin):
    list_display = ("order", "employer", "worker", "status", "expires_at", "created_at")
    list_filter = ("status",)
