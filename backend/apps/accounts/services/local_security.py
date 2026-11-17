"""Single-account local emergency rotation; never rotates global signing keys."""
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from apps.accounts.models import AccountStatus, User
from apps.accounts.services.auth_service import _blacklist_all_user_tokens


def rotate_local_admin_password(account_id, new_password):
    if getattr(settings, "IS_PRODUCTION", False) or getattr(settings, "LOCAL_TARGET_KIND", "") != "work":
        raise ImproperlyConfigured("Emergency rotation is restricted to the explicit local working settings.")
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=account_id)
        if not user.is_admin_user or not user.is_active or user.is_anonymized or user.account_status != AccountStatus.ACTIVE:
            raise ValidationError("The target must be an active, non-anonymized local administrator.")
        validate_password(new_password, user=user)
        if user.check_password(new_password):
            raise ValidationError("The new password must differ from the exposed password.")
        user.set_password(new_password)
        user.token_version += 1
        user.save(update_fields=["password", "token_version", "updated_at"])
        _blacklist_all_user_tokens(user)
    # Django's password-derived session authentication hash also invalidates
    # existing operator-browser sessions when they next authenticate.
    return user.pk
