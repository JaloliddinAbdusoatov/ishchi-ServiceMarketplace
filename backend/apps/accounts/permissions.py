from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsActiveAccount(BasePermission):
    message = "Active, non-anonymized user account required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
        )


class IsWorker(BasePermission):
    message = "Worker capability is required for this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
            and user.is_worker
        )


class IsVerifiedWorker(BasePermission):
    """
    DEPRECATED FOR MARKETPLACE ACCESS (Batch 16 / PDR-PRODUCT-14 / Option A).

    KYC is optional; workers do not require verification to apply for orders or accept invitations.
    Use IsWorker for marketplace operations.
    """
    message = "Verified worker trust badge required for this specific resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
            and user.is_verified_worker
        )


class IsEmployer(BasePermission):
    message = "Employer capability is required for this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
            and user.is_employer
        )


class IsAdminUserRole(BasePermission):
    message = "Administrator privileges are required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
            and user.is_admin_user
        )


class IsAdminOrReadOnly(BasePermission):
    message = "Only administrators can modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not user.is_anonymized
            and user.account_status == "ACTIVE"
            and user.is_admin_user
        )
