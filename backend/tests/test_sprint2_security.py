"""Offline regressions: no network and no PostgreSQL or Redis connection."""
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from apps.common.db_backends.postgresql.base import DatabaseWrapper
from apps.common.redis_backend import RedisCache
from apps.common.redis_backend import redis_target


def forged_approval(tmp_path, monkeypatch, variable, target, operations):
    path = tmp_path / "self-generated.json"
    path.write_text(json.dumps({"target": target, "approved_by": "self-claimed-owner",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "operations": operations, "disposable": True}))
    monkeypatch.setenv(variable, str(path))


def test_self_generated_file_cannot_enable_production_postgres(tmp_path, monkeypatch):
    target = {"dbname": "ishchi_marketplace_sprint1_offline", "host": "db.invalid", "port": "5432", "user": "runtime"}
    forged_approval(tmp_path, monkeypatch, "DB_AUTHORIZATION_FILE", target, ["connect", "test_schema"])
    with override_settings(IS_PRODUCTION=True, POSTGRES_INTEGRATION=True), patch(
        "django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection"
    ) as driver:
        wrapper = DatabaseWrapper({})
        with pytest.raises(ImproperlyConfigured, match="local attestations cannot grant"):
            wrapper.get_new_connection(target)
        with patch.object(wrapper, "get_connection_params", return_value=target):
            with pytest.raises(ImproperlyConfigured, match="local attestations cannot grant"):
                wrapper.schema_editor()
        driver.assert_not_called()


def test_self_generated_file_cannot_enable_production_redis(tmp_path, monkeypatch):
    target = {"host": "cache.invalid", "port": 6379, "database": 15, "user": "default"}
    forged_approval(tmp_path, monkeypatch, "REDIS_AUTHORIZATION_FILE", target, ["cache", "cache_test"])
    with override_settings(IS_PRODUCTION=True):
        cache = RedisCache("rediss://default:synthetic@cache.invalid:6379/15", {})
        with patch.object(cache, "_client_cls") as client:
            with pytest.raises(ImproperlyConfigured, match="local attestations cannot grant"):
                cache.get("private-key")
            client.assert_not_called()


@pytest.mark.parametrize("url", ["redis://default:secret@cache.invalid:6379/15", "rediss://cache.invalid:6379/15",
    "rediss://default:secret@cache.invalid:6379/15?ssl_cert_reqs=none", "rediss://default:secret@cache.invalid:6379/-1"])
def test_redis_rejects_insecure_or_unauthenticated_transport(url):
    with pytest.raises(ImproperlyConfigured):
        redis_target(url)


def test_redis_authorization_uses_decoded_transport_identity():
    assert redis_target("rediss://%64efault:synthetic@cache.invalid:6379/15") == {
        "host": "cache.invalid", "port": 6379, "database": 15, "user": "default"}


def test_replica_list_cannot_bypass_single_target_interlock():
    cache = RedisCache(["rediss://default:synthetic@approved.invalid:6379/15",
                        "rediss://default:synthetic@unapproved.invalid:6379/15"], {})
    with patch.object(cache, "_client_cls") as client:
        with pytest.raises(ImproperlyConfigured, match="one explicitly approved"):
            cache.get("synthetic")
        client.assert_not_called()


@pytest.mark.parametrize("operation", ["create_test_db", "clone_test_db", "destroy_test_db"])
def test_django_database_lifecycle_is_blocked_before_connection(operation):
    wrapper = DatabaseWrapper({})
    with patch.object(wrapper, "ensure_connection") as connection:
        with pytest.raises(ImproperlyConfigured, match="Automatic PostgreSQL"):
            getattr(wrapper.creation, operation)()
        connection.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["application", "invitation"])
def test_unavailable_worker_cannot_be_hired_even_with_stale_objects(employer_pair, unverified_worker, published_order, path):
    from apps.applications.services import ApplicationService
    from apps.invitations.services import InvitationService
    from apps.profiles.models import WorkerProfile
    from apps.common.exceptions import ConflictError
    _, employer = employer_pair
    _, worker = unverified_worker
    app = ApplicationService.submit_application(worker, published_order.pk, "Synthetic", 100)
    invitation = InvitationService.send_invitation(employer, published_order.pk, worker.pk)
    WorkerProfile.objects.filter(pk=worker.pk).update(is_available=False)
    with pytest.raises(ConflictError) as error:
        if path == "application":
            ApplicationService.accept_application(app.pk, employer)
        else:
            InvitationService.accept_invitation(invitation.pk, worker)
    assert error.value.get_codes() == "worker_unavailable"
    published_order.refresh_from_db()
    app.refresh_from_db()
    invitation.refresh_from_db()
    assert published_order.hired_worker_count == 0
    assert app.status == invitation.status == "PENDING"


@pytest.mark.django_db
def test_deletion_audit_cannot_be_added_changed_or_deleted_through_admin(client, admin_user):
    from apps.accounts.models import AccountDeletionAudit
    row = AccountDeletionAudit.objects.create(user_id=admin_user.pk, phone_hash="0" * 64,
        role="WORKER", reason="Synthetic retention", performed_by_id=admin_user.pk)
    client.force_login(admin_user)
    root = "/django-admin/accounts/accountdeletionaudit/"
    assert client.get(root).status_code == 200
    assert client.post(root + "add/", {}).status_code == 403
    assert client.post(root + f"{row.pk}/change/", {"reason": "tampered"}).status_code == 403
    assert client.post(root + f"{row.pk}/delete/", {"post": "yes"}).status_code == 403
    client.post(root, {"action": "delete_selected", "_selected_action": str(row.pk), "post": "yes"})
    row.refresh_from_db()
    assert row.reason == "Synthetic retention"


@pytest.mark.django_db
@pytest.mark.parametrize("failure", [RedisConnectionError, RedisTimeoutError])
@pytest.mark.parametrize("action", ["login", "authenticated", "otp"])
def test_security_cache_outage_fails_closed_without_leaking_details(api_client, auth_client, unverified_worker, failure, action):
    user, _ = unverified_worker
    client = auth_client(user) if action == "authenticated" else api_client
    with patch("django.core.cache.backends.locmem.LocMemCache.get", side_effect=failure("private-cache-password")), patch(
        "apps.accounts.services.otp_service.get_sms_provider"
    ) as sms:
        if action == "authenticated":
            result = client.get("/api/v1/auth/me/")
        elif action == "login":
            result = client.post("/api/v1/auth/login/", {"phone_number": user.phone_number, "password": "StrongPass2026!"}, format="json")
        else:
            result = client.post("/api/v1/auth/otp/send/", {"phone_number": user.phone_number}, format="json")
        assert result.status_code == 503, result.data
        assert result.data["error"]["code"] == "service_unavailable"
        assert "private-cache-password" not in str(result.data)
        sms.assert_not_called()
