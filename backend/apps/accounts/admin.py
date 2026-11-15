from django.contrib import admin
from apps.accounts.models import AccountDeletionAudit, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_number", "full_name", "role", "account_status", "is_phone_verified", "is_anonymized")
    list_filter = ("role", "account_status", "is_phone_verified", "is_anonymized")
    search_fields = ("phone_number", "full_name", "email")


@admin.register(AccountDeletionAudit)
class AccountDeletionAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "role", "performed_by_id", "created_at")
    readonly_fields = ("id", "user_id", "phone_hash", "role", "reason", "performed_by_id", "created_at")
