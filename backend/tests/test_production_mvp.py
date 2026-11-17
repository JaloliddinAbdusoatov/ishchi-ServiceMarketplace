"""Offline API/ORM and configuration regressions. No external service is contacted."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import User
from apps.accounts.services.auth_service import generate_jwt_pair
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.sms_service import SMSUnavailable, get_sms_provider
from apps.common.db_backends.postgresql.base import DatabaseWrapper
from apps.common.db_router import PendingSchemaApprovalRouter
from tests.conftest import UserFactory


PAYLOAD = {"phone_number": "+998931234567", "full_name": "Marketplace Customer",
           "password": "NewAccount2026!", "role": "EMPLOYER"}


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["WORKER", "EMPLOYER"])
def test_registration_activates_immediately_without_sms_or_admin_approval(api_client, role):
    payload = {**PAYLOAD, "role": role}
    with override_settings(SMS_BACKEND="disabled"), patch(
        "apps.accounts.services.otp_service.get_sms_provider", side_effect=SMSUnavailable
    ) as provider:
        registered = api_client.post("/api/v1/auth/register/", payload, format="json")
        provider.assert_not_called()
    assert registered.status_code == 201
    user = User.objects.get(phone_number=payload["phone_number"])
    assert user.is_active and user.account_status == "ACTIVE"
    assert not user.is_phone_verified
    assert registered.data["data"]["user"]["is_phone_verified"] is False
    tokens = registered.data["data"]["tokens"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.get("/api/v1/auth/me/").status_code == 200
    assert api_client.get("/api/v1/admin/dashboard/").status_code == 403
    refresh = api_client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert refresh.status_code == 200
    api_client.credentials()
    assert api_client.post("/api/v1/auth/login/", payload, format="json").status_code == 200
    assert cache.get(f"otp_session:VERIFY_PHONE:{user.phone_number}") is None


@pytest.mark.django_db
def test_optional_otp_delivery_failure_invalidates_code():
    phone = PAYLOAD["phone_number"]
    with patch("apps.accounts.services.otp_service.get_sms_provider", side_effect=SMSUnavailable):
        with pytest.raises(SMSUnavailable):
            OTPService.send_otp(phone)
    assert cache.get(f"otp_session:VERIFY_PHONE:{phone}") is None


@pytest.mark.django_db
@pytest.mark.parametrize("changes", [{"is_active": False}, {"account_status": "SUSPENDED"}, {"is_anonymized": True, "phone_number": None}])
def test_disabled_accounts_cannot_login_refresh_or_access(api_client, changes):
    user = UserFactory()
    tokens = generate_jwt_pair(user)
    User.objects.filter(pk=user.pk).update(**changes)
    response = api_client.post("/api/v1/auth/login/", {"phone_number": user.phone_number, "password": "StrongPass2026!"}, format="json")
    assert response.status_code in (401, 403)
    assert api_client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.get("/api/v1/notifications/").status_code == 401


@pytest.mark.django_db
def test_suspended_account_cannot_be_reactivated_by_phone_otp(api_client):
    user = UserFactory(account_status="SUSPENDED")
    with patch("apps.accounts.services.otp_service.get_sms_provider") as provider:
        OTPService.send_otp(user.phone_number)
    code = provider.return_value.send_otp.call_args.args[1]
    assert api_client.post("/api/v1/auth/otp/verify/", {"phone_number": user.phone_number, "otp": code}, format="json").status_code == 401
    user.refresh_from_db()
    assert user.account_status == "SUSPENDED"


@pytest.mark.django_db
def test_logout_revokes_entire_rotated_session_but_preserves_other_session(api_client):
    user = UserFactory()
    first = generate_jwt_pair(user)
    separate = generate_jwt_pair(user)
    rotated = api_client.post("/api/v1/auth/token/refresh/", {"refresh": first["refresh"]}, format="json").data["data"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated['access']}")
    assert api_client.post("/api/v1/auth/logout/", {"refresh": rotated["refresh"]}, format="json").status_code == 200
    for access in (first["access"], rotated["access"]):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert api_client.get("/api/v1/auth/me/").status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {separate['access']}")
    assert api_client.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_expired_tokens_and_missing_version_are_rejected(api_client):
    user = UserFactory()
    tokens = generate_jwt_pair(user)
    access = AccessToken(tokens["access"])
    access["exp"] = 1
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api_client.get("/api/v1/auth/me/").status_code == 401
    refresh = RefreshToken(tokens["refresh"])
    del refresh["token_version"]
    assert api_client.post("/api/v1/auth/token/refresh/", {"refresh": str(refresh)}, format="json").status_code == 401


@pytest.mark.django_db
def test_account_update_and_role_endpoint_cannot_grant_admin(auth_client, unverified_worker):
    user, _ = unverified_worker
    client = auth_client(user)
    client.patch("/api/v1/auth/me/", {"role": "ADMIN", "is_staff": True, "is_superuser": True}, format="json")
    assert client.post("/api/v1/auth/enable-role/", {"role": "ADMIN"}, format="json").status_code == 400
    user.refresh_from_db()
    assert user.role == "WORKER" and not user.is_staff and not user.is_superuser
    assert client.get("/api/v1/admin/users/").status_code == 403


@pytest.mark.django_db
def test_django_admin_uses_real_account_boundaries(admin_user):
    assert authenticate(phone_number=admin_user.phone_number, password="AdminPass2026!") == admin_user
    admin_user.account_status = "SUSPENDED"
    admin_user.save(update_fields=["account_status"])
    assert authenticate(phone_number=admin_user.phone_number, password="AdminPass2026!") is None


@pytest.mark.django_db
def test_private_chat_attachments_require_current_participation(auth_client, employer_pair, unverified_worker, published_order, tmp_path):
    from apps.applications.models import OrderApplication
    from apps.chat.services import ChatService
    worker_user, worker = unverified_worker
    employer_user, _ = employer_pair
    app = OrderApplication.objects.create(order=published_order, worker=worker, proposed_price=100)
    conv, _ = ChatService.get_or_create_conversation(worker_user, published_order.pk)
    with override_settings(MEDIA_ROOT=tmp_path):
        message = ChatService.send_message(conv, worker_user, attachment=SimpleUploadedFile("note.txt", b"Private note"))
        url = f"/api/v1/chat/messages/{message.pk}/attachment/"
        assert APIClient().get(url).status_code == 401
        assert auth_client(UserFactory()).get(url).status_code == 403
        for user in (worker_user, employer_user):
            response = auth_client(user).get(url)
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"Private note"
            response.close()
        app.status = "WITHDRAWN"
        app.save(update_fields=["status"])
        assert auth_client(worker_user).get(url).status_code == 403


@pytest.mark.django_db
def test_payments_never_accept_submission_and_health_hides_internal_errors(api_client):
    assert api_client.get("/api/v1/payments/status/").data["data"]["enabled"] is False
    for path in ("/api/v1/payments/status/", "/api/v1/payments/", "/api/v1/payments/submit/"):
        assert api_client.post(path, {"amount": 100}, format="json").status_code in (404, 405)
    with patch("apps.common.views.connection.cursor", side_effect=RuntimeError("secret-db-password")):
        response = api_client.get("/api/v1/health/")
    assert response.status_code == 503
    assert "secret-db-password" not in str(response.data)
    assert "version" not in response.data["database"] and "name" not in response.data["database"]


def test_production_rejects_memory_sms_even_with_debug_and_local_flags():
    with override_settings(IS_PRODUCTION=True, DEBUG=True, LOCAL_DEVELOPMENT=True, SMS_BACKEND="memory"):
        with pytest.raises(SMSUnavailable):
            get_sms_provider()


def test_http_sms_adapter_contract_and_sanitized_failure(caplog):
    from urllib.error import URLError
    from apps.accounts.services.sms_service import HTTPSMSProvider
    with override_settings(SMS_BACKEND="http", SMS_API_URL="https://gateway.invalid/send", SMS_API_TOKEN="private-token"):
        with patch("apps.accounts.services.sms_service.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 202
            get_sms_provider().send_otp("+998931234567", "234567", "VERIFY_PHONE", 300)
            request = opener.return_value.open.call_args.args[0]
            assert json.loads(request.data)["code"] == "234567"
            assert request.get_header("Authorization") == "Bearer private-token"
            assert opener.return_value.open.call_args.kwargs["timeout"] == 10
            opener.return_value.open.side_effect = URLError("private-token 234567")
            with pytest.raises(SMSUnavailable) as error:
                HTTPSMSProvider().send_otp("+998931234567", "234567", "VERIFY_PHONE", 300)
    assert "private-token" not in str(error.value) + caplog.text
    assert "234567" not in str(error.value) + caplog.text


def test_only_explicitly_trusted_proxy_can_set_client_ip():
    from types import SimpleNamespace
    from apps.accounts.views import _get_client_ip
    request = SimpleNamespace(META={"REMOTE_ADDR": "127.0.0.1", "HTTP_X_REAL_IP": "203.0.113.5"})
    assert _get_client_ip(request) == "127.0.0.1"
    with override_settings(TRUSTED_PROXY_IPS=["127.0.0.1"]):
        assert _get_client_ip(request) == "203.0.113.5"
        request.META["HTTP_X_REAL_IP"] = "malformed"
        assert _get_client_ip(request) == "127.0.0.1"


@pytest.mark.django_db
def test_otp_expiration_attempt_limit_and_hashed_storage():
    phone = "+998931234567"
    UserFactory(phone_number=phone)
    with patch("apps.accounts.services.otp_service.get_sms_provider") as provider:
        assert OTPService.send_otp(phone)["success"]
        code = provider.return_value.send_otp.call_args.args[1]
    session = cache.get(f"otp_session:VERIFY_PHONE:{phone}")
    assert code not in str(session)
    with patch("apps.accounts.services.otp_service.time.time", return_value=session["expires_at"] + 1):
        assert OTPService.verify_otp(phone, code)[0] is False
    cache.clear()
    with patch("apps.accounts.services.otp_service.get_sms_provider"):
        OTPService.send_otp(phone)
    for _ in range(5):
        assert OTPService.verify_otp(phone, "000000")[0] is False
    assert cache.get(f"otp_session:VERIFY_PHONE:{phone}") is None


def test_seed_command_rejected_before_any_transaction_or_query():
    with override_settings(IS_PRODUCTION=True):
        with pytest.raises(CommandError, match="local SQLite"):
            call_command("seed_demo")


@pytest.mark.parametrize("name", ["ishchi_test", "postgres", "ishchi_marketplace dbname=ishchi_test", "postgresql://host/ishchi_test"])
def test_database_guard_rejects_before_driver_connection(name, settings):
    wrapper = DatabaseWrapper(settings.DATABASES["default"].copy())
    with patch("django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection") as connect:
        with pytest.raises(ImproperlyConfigured):
            wrapper.get_new_connection({"dbname": name, "host": "localhost", "port": "5432", "user": "runtime"})
        connect.assert_not_called()


def test_production_router_blocks_unapproved_schema_changes():
    assert PendingSchemaApprovalRouter().allow_migrate("default", "accounts") is False
    with pytest.raises(ImproperlyConfigured, match="separately approved"):
        DatabaseWrapper({}).schema_editor()
    with override_settings(IS_PRODUCTION=True):
        with pytest.raises(CommandError, match="separately approved"):
            call_command("migrate", skip_checks=True)


def production_environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "DB_", "SMS_", "ISHCHI_"))}
    env.update({"DJANGO_SETTINGS_MODULE": "config.settings.production", "ISHCHI_ENV": "production",
        "DJANGO_SECRET_KEY": "test-only-" + "s4N8kP9x7" * 8, "DJANGO_ALLOWED_HOSTS": "api.example.uz",
        "CSRF_TRUSTED_ORIGINS": "https://example.uz", "CORS_ALLOWED_ORIGINS": "https://example.uz",
        "DB_NAME": "ishchi_marketplace", "DB_USER": "runtime", "DB_PASSWORD": "test-only",
        "DB_HOST": "db.invalid", "DB_PORT": "5432", "DB_SSLROOTCERT": str(Path(__file__).parent / "fixtures" / "public-test-ca.pem"),
        "REDIS_URL": "rediss://default:synthetic-test-only@cache.invalid:6379/1", "SMS_BACKEND": "http",
        "SMS_API_URL": "https://sms.invalid/send", "SMS_API_TOKEN": "test-only"})
    return env


@pytest.mark.parametrize("override,valid", [({}, True), ({"SMS_BACKEND": "disabled", "SMS_API_URL": "", "SMS_API_TOKEN": ""}, True),
    ({"SMS_BACKEND": "memory"}, False),
    ({"SMS_API_TOKEN": ""}, False), ({"SMS_API_URL": "http://sms.invalid"}, False),
    ({"DJANGO_SECRET_KEY": ""}, False), ({"DJANGO_ALLOWED_HOSTS": "*"}, False),
    ({"CORS_ALLOWED_ORIGINS": "https://*.example.uz"}, False), ({"DB_NAME": "ishchi_test"}, False),
    ({"CSRF_TRUSTED_ORIGINS": "http://example.uz"}, False),
    ({"REDIS_KEY_PREFIX": "*"}, False)])
def test_production_startup_configuration_without_network(override, valid):
    env = production_environment()
    env.update(override)
    result = subprocess.run([sys.executable, "-c", """
import socket
def denied(*args, **kwargs):
    raise AssertionError('Network connection attempted')
socket.socket.connect = denied
from django.conf import settings
assert settings.DEBUG is False
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert settings.SECURE_SSL_REDIRECT
assert settings.SIMPLE_JWT['ROTATE_REFRESH_TOKENS'] and settings.SIMPLE_JWT['BLACKLIST_AFTER_ROTATION']
assert settings.SMS_BACKEND in {'disabled', 'http'}
import django
django.setup()
from django.core.management import get_commands, call_command
assert 'seed_demo' not in get_commands()
call_command('check', deploy=True, tags=['security'], fail_level='WARNING')
"""], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=15)
    assert (result.returncode == 0) == valid, result.stderr
