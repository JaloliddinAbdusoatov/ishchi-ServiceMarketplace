from django.contrib import admin
from django.contrib.admin.models import LogEntry
from apps.accounts.models import AccountDeletionAudit, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_number", "full_name", "role", "account_status", "is_phone_verified", "is_anonymized")
    list_filter = ("role", "account_status", "is_phone_verified", "is_anonymized")
    search_fields = ("phone_number", "full_name", "email")

    # Account writes use the reviewed APIs; provisioning uses createsuperuser.
    # A generic ModelAdmin otherwise permits raw password/privilege edits and
    # hard deletion that bypasses anonymization and session revocation.
    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class AdministrativeAuditAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user_id", "content_type", "object_id", "change_message")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccountDeletionAudit)
class AccountDeletionAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "role", "performed_by_id", "created_at")
    readonly_fields = ("id", "user_id", "phone_hash", "role", "reason", "performed_by_id", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
