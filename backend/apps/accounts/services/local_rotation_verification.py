"""Owner-approved interactive verification. Secrets live only in process memory."""
from django.conf import settings
from django.core.management.base import CommandError
from django.test import Client
from apps.accounts.models import User
from apps.accounts.services.auth_service import generate_jwt_pair


def prepare_verification(account_id, previous, *, allow_unknown_previous=False):
    if settings.IS_PRODUCTION or getattr(settings, "LOCAL_TARGET_KIND", "") != "work":
        raise CommandError("Local working administrator verification only.")
    user = User.objects.get(pk=account_id)
    if not user.is_admin_user or not user.is_active:
        raise CommandError("Active administrator required; no rotation performed.")
    if not (allow_unknown_previous and previous is None) and (not previous or not user.check_password(previous)):
        raise CommandError("Previous credential/admin validation failed; no rotation performed.")
    others = list(User.objects.exclude(pk=account_id).order_by("pk").values("pk", "password", "token_version", "is_active", "account_status"))
    key = settings.SECRET_KEY
    browser = Client(HTTP_HOST="localhost")
    browser.force_login(user)
    if browser.get("/django-admin/").status_code != 200:
        raise CommandError("Pre-rotation admin session verification failed.")
    tokens = generate_jwt_pair(user)

    def verify(new_password):
        client = Client(HTTP_HOST="localhost")
        checks = [browser.get("/django-admin/").status_code == 302]
        checks.append(client.get("/api/v1/admin/dashboard/", HTTP_AUTHORIZATION="Bearer " + tokens["access"]).status_code == 401)
        checks.append(client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, content_type="application/json").status_code == 401)
        if previous is not None:
            checks.append(client.post("/api/v1/auth/login/", {"phone_number": user.phone_number, "password": previous}, content_type="application/json").status_code == 401)
        response = client.post("/api/v1/auth/login/", {"phone_number": user.phone_number, "password": new_password}, content_type="application/json")
        checks.append(response.status_code == 200)
        if response.status_code == 200:
            access = response.json()["data"]["tokens"]["access"]
            checks.append(client.get("/api/v1/admin/dashboard/", HTTP_AUTHORIZATION="Bearer " + access).status_code == 200)
        checks.append(browser.login(phone_number=user.phone_number, password=new_password))
        checks.append(browser.get("/django-admin/").status_code == 200)
        checks.append(key == settings.SECRET_KEY)
        checks.append(others == list(User.objects.exclude(pk=account_id).order_by("pk").values("pk", "password", "token_version", "is_active", "account_status")))
        if not all(checks):
            raise CommandError("Password WAS rotated, but verification FAILED; keep the new password and investigate. No automatic rollback to exposed credentials.")
    return verify
