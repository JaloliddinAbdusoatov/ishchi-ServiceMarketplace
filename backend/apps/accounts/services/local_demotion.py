"""Exact-account demotion, only via separately approved local operator action."""
import uuid
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.contrib.sessions.models import Session
from apps.accounts.models import User, UserRole, AccountStatus
from apps.accounts.services.auth_service import _blacklist_all_user_tokens
from apps.accounts.services.audit_service import record_admin_action

SYNTHETIC = uuid.UUID("489124fe-ae1b-4551-8495-9f148c46490b")
OWNER = uuid.UUID("319cb674-96bc-4de3-bf08-e6c4462500f7")


def demote_local_verification_admin(account_id, actor_id, *, owner_approved=False):
    if not owner_approved:
        raise ValidationError("Separate explicit owner approval is required.")
    if getattr(settings,"IS_PRODUCTION",False) or getattr(settings,"LOCAL_TARGET_KIND","")!="work":
        raise ImproperlyConfigured("Only the approved local working environment is allowed.")
    if str(account_id)!=str(SYNTHETIC) or str(actor_id)!=str(OWNER):
        raise ValidationError("Only the exact synthetic subject and owner actor are allowed.")
    with transaction.atomic():
        users={u.pk:u for u in User.objects.select_for_update().filter(pk__in=[SYNTHETIC,OWNER]).order_by("pk")}
        target,owner=users.get(SYNTHETIC),users.get(OWNER)
        if not owner or not (owner.is_admin_user and owner.is_superuser and owner.is_active
                and not owner.is_anonymized and owner.account_status==AccountStatus.ACTIVE and owner.has_usable_password()):
            raise ValidationError("A separate active owner administrator must remain usable.")
        if not target or not (target.is_admin_user and target.is_superuser and target.is_active and not target.is_anonymized and target.account_status==AccountStatus.ACTIVE):
            raise ValidationError("Subject no longer matches the reviewed privileged account; refusing replay.")
        before={k:getattr(target,k) for k in ("role","is_staff","is_superuser","has_worker_role","has_employer_role","token_version")}
        before["groups"]=list(target.groups.values_list("pk",flat=True))
        before["permissions"]=list(target.user_permissions.values_list("pk",flat=True))
        target.is_staff=False
        target.is_superuser=False
        target.role=UserRole.WORKER  # Current model has no neutral/non-role enum.
        target.token_version+=1
        target.save(update_fields=["role","is_staff","is_superuser","token_version","updated_at"])
        if before["groups"]:target.groups.clear()
        if before["permissions"]:target.user_permissions.clear()
        _blacklist_all_user_tokens(target)
        for session in Session.objects.all().iterator():
            if str(session.get_decoded().get("_auth_user_id"))==str(target.pk):
                session.delete()
        record_admin_action(owner,"account.local_verification_admin.demoted",target)
    return {"subject":str(target.pk),"before":before,"after_role":"WORKER","sessions_revoked":True}
