"""Offline infrastructure and actual SQLite/API smoke regressions."""
from datetime import datetime, timedelta, timezone as datetime_timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO, StringIO
from pathlib import Path
import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from redis.exceptions import ConnectionError as RedisConnectionError

from apps.accounts.services.auth_service import AuthService
from apps.common.media_erasure import process_media_erasure
from apps.common.middleware import request_id
from apps.common.models import MediaDeletionTask

ROOT = Path(__file__).resolve().parents[2]


def load_deploy_module(name):
    spec = spec_from_file_location(name, ROOT / "deploy" / (name + ".py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ops = load_deploy_module("ops")


def test_infrastructure_invariants():
    load_deploy_module("check_config").check()


@pytest.mark.parametrize("fault", ["public-port", "root", "writable-root", "private-media"])
def test_infrastructure_check_rejects_unsafe_configuration(tmp_path, fault):
    import yaml
    files = ("deploy/compose.production.yml", "deploy/nginx.conf.example", "deploy/redis/redis.conf.example",
        "deploy/redis/users.acl.example", "backend/Dockerfile", "frontend/Dockerfile", "backend/.dockerignore",
        "frontend/.dockerignore", "backend/config/gunicorn.py")
    for name in files:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((ROOT / name).read_text())
    path = tmp_path / "deploy/compose.production.yml"
    document = yaml.safe_load(path.read_text())
    if fault == "public-port":
        document["services"]["backend"]["ports"] = ["8000:8000"]
    elif fault == "root":
        document["services"]["backend"]["user"] = "0:0"
    elif fault == "writable-root":
        document["services"]["gateway"]["read_only"] = False
    else:
        nginx = tmp_path / "deploy/nginx.conf.example"
        nginx.write_text(nginx.read_text().replace("location ^~ /media/chat/ { return 404; }", ""))
    path.write_text(yaml.safe_dump(document))
    with pytest.raises(AssertionError):
        load_deploy_module("check_config").check(tmp_path)


@pytest.mark.parametrize("name", ["ishchi_test", "postgres", "ishchi_marketplace dbname=postgres", "postgresql://host/db"])
def test_operational_plans_reject_legacy_and_dsn_targets(name):
    with pytest.raises(ValueError):
        ops.database_target("db.invalid", 5432, name, "backup")


def test_backup_plan_encrypts_stream_without_credentials_or_execution(tmp_path):
    target = ops.database_target("db.invalid", 5432, "ishchi_marketplace", "backup")
    plan = ops.backup_plan(target, tmp_path, "age1" + "a" * 58)
    assert plan["pipeline"][0][:3] == ["pg_dump", "--no-password", "--format=custom"]
    assert plan["pipeline"][1][0] == "age" and plan["pipeline"][1][-1].endswith(".age.partial")
    assert "NOT_GRANTED" in plan["authorization"] and plan["execution"].startswith("BLOCKED")
    assert plan["clear_environment_prefixes"] == ["PG"]
    assert not list(tmp_path.iterdir())


def test_restore_can_only_target_separately_provisioned_isolated_database(tmp_path):
    archive = tmp_path / "ishchi-database-20261101T000000Z-1234abcd.dump.age"
    with pytest.raises(ValueError):
        ops.restore_plan({"host": "db.invalid", "port": 5432, "database": "ishchi_marketplace", "user": "restore"}, archive, tmp_path / "key")
    target = ops.database_target("restore.invalid", 5432, "ishchi_marketplace_restore_trial", "restore", restore=True)
    plan = ops.restore_plan(target, archive, tmp_path / "key")
    assert not plan["recovery_verified"] and plan["execution"].startswith("BLOCKED")
    command = plan["pipeline"][1]
    assert "--single-transaction" in command and "--clean" not in command and "--create" not in command


def test_media_backup_and_restore_are_inert_and_select_explicit_targets(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "synthetic.txt").write_text("Synthetic test data")
    plan = ops.media_backup_plan(source, tmp_path, "age1" + "a" * 58)
    assert plan["pipeline"][0][0] == "tar" and plan["pipeline"][1][0] == "age"
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    restore = ops.media_restore_plan(tmp_path / "ishchi-media-20261101T000000Z-1234abcd.tar.age", isolated, tmp_path / "key")
    assert restore["extraction_execution"].startswith("BLOCKED") and not restore["recovery_verified"]
    assert (source / "synthetic.txt").exists() and not list(isolated.iterdir())
    (isolated / "existing.txt").write_text("Preserve existing data")
    with pytest.raises(ValueError):
        ops.media_restore_plan(tmp_path / "ishchi-media-20261101T000000Z-1234abcd.tar.age", isolated, tmp_path / "key")


@pytest.mark.parametrize("nested", [False, True])
def test_media_backup_cannot_archive_its_own_output(tmp_path, nested):
    destination = tmp_path / "nested" if nested else tmp_path
    destination.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="outside the media source tree"):
        ops.media_backup_plan(tmp_path, destination, "age1" + "a" * 58)


def test_retention_only_lists_expired_encrypted_artifacts(tmp_path):
    expired = tmp_path / "ishchi-database-20261001T000000Z-1234abcd.dump.age"
    recent = tmp_path / "ishchi-media-20261115T000000Z-1234abcd.tar.age"
    unrelated = tmp_path / "important.txt"
    partial = tmp_path / (expired.name + ".partial")
    for path in (expired, recent, unrelated, partial):
        path.write_bytes(b"Synthetic fixture, not a real backup")
    plan = ops.retention_plan(tmp_path, now=datetime(2026, 11, 16, tzinfo=datetime_timezone.utc))
    assert plan["candidates"] == [str(expired)] and plan["deleted"] == 0
    assert all(path.exists() for path in (expired, recent, unrelated, partial))


def test_encrypted_checksum_verification_is_not_restore_certification(tmp_path):
    archive = tmp_path / "ishchi-database-20261101T000000Z-1234abcd.dump.age"
    data = b"age-encryption.org/v1\nSYNTHETIC HEADER FIXTURE ONLY"
    archive.write_bytes(data)
    result = ops.verify_archive(archive, hashlib.sha256(data).hexdigest())
    assert result["checksum_matches"] and not result["recovery_verified"]
    with pytest.raises(ValueError):
        ops.verify_archive(archive, "0" * 64)


def test_secret_scanner_detects_keys_without_exposing_values():
    scanner = load_deploy_module("scan_secrets")
    secret = "ghp_" + "a" * 36
    findings = scanner.scan_text("source.py", 'TOKEN = "' + secret + '"')
    assert findings == [("github-token", "source.py", 1)] and secret not in str(findings)


@pytest.mark.django_db
def test_liveness_does_not_touch_databases_or_security_cache(api_client):
    with patch("apps.common.views.connection.cursor", side_effect=AssertionError("Database accessed")) as database, \
         patch("apps.common.views.cache.set", side_effect=AssertionError("Cache accessed")) as cache:
        response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200 and response.data == {"success": True, "service": "ishchi-backend"}
    database.assert_not_called()
    cache.assert_not_called()


@pytest.mark.django_db
def test_readiness_is_unavailable_without_leaking_dependency_errors(api_client):
    with patch("apps.common.views.connection.cursor", side_effect=OSError("private-db-details")), \
         patch("apps.common.views.cache.set", side_effect=RedisConnectionError("private-cache-details")):
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 503 and "private-" not in str(response.data)


@pytest.mark.django_db
def test_request_ids_and_logs_do_not_trust_incoming_secrets_or_log_queries(api_client, caplog):
    response = api_client.get("/api/v1/payments/status/?token=private-query-secret",
        HTTP_X_REQUEST_ID="private-client-secret", HTTP_AUTHORIZATION="")
    identifier = response["X-Request-ID"]
    assert len(identifier) == 32 and identifier != "private-client-secret"
    assert "private-query-secret" not in caplog.text and "private-client-secret" not in caplog.text
    assert "api-v1:payment-status" in caplog.text and request_id.get() == "-"
    with override_settings(TRUSTED_PROXY_IPS=["127.0.0.1"]):
        response = api_client.get("/api/v1/health/live/", HTTP_X_REQUEST_ID="a" * 32)
    assert response["X-Request-ID"] == "a" * 32


@pytest.mark.django_db
def test_media_erasure_survives_storage_failure_and_retries(unverified_worker, tmp_path, django_capture_on_commit_callbacks, caplog):
    user, worker = unverified_worker
    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="PNG")
    with override_settings(MEDIA_ROOT=tmp_path):
        worker.photo.save("erase.png", SimpleUploadedFile("erase.png", image.getvalue()), save=True)
        name = worker.photo.name
        with patch("apps.common.media_erasure.default_storage.delete", side_effect=OSError("private-storage-path")):
            with django_capture_on_commit_callbacks(execute=True):
                AuthService.anonymize_and_delete_account(user, require_password=False)
        task = MediaDeletionTask.objects.get()
        user.refresh_from_db()
        assert user.is_anonymized and task.completed_at is None and task.attempts == 1
        assert task.error_code == "OSError" and "private-storage-path" not in caplog.text
        assert (tmp_path / name).exists()
        task.next_attempt_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=["next_attempt_at"])
        assert process_media_erasure() == {"completed": 1, "failed": 0}
        task.refresh_from_db()
        assert task.completed_at is not None and task.attempts == 2 and task.name == "" and not (tmp_path / name).exists()


@pytest.mark.django_db
def test_media_erasure_task_rolls_back_when_audit_fails(unverified_worker, tmp_path):
    user, worker = unverified_worker
    with override_settings(MEDIA_ROOT=tmp_path):
        worker.photo.name = "workers/photos/synthetic.png"
        worker.save(update_fields=["photo"])
        with patch("apps.accounts.services.auth_service.AccountDeletionAudit.objects.create", side_effect=RuntimeError("audit failure")):
            with pytest.raises(RuntimeError):
                AuthService.anonymize_and_delete_account(user, require_password=False)
    assert not MediaDeletionTask.objects.exists()


@pytest.mark.django_db
def test_media_cleanup_is_dry_by_default_and_requires_exact_root(tmp_path):
    task = MediaDeletionTask.objects.create(name="workers/photos/synthetic.png")
    output = StringIO()
    with override_settings(MEDIA_ROOT=tmp_path):
        call_command("retry_media_erasure", stdout=output)
        assert "DRY RUN: 1" in output.getvalue()
        with pytest.raises(CommandError, match="exact --confirm-media-root"):
            call_command("retry_media_erasure", apply=True, confirm_media_root=str(tmp_path / "other"))
    task.refresh_from_db()
    assert task.attempts == 0 and task.completed_at is None


@pytest.mark.django_db
def test_erasure_cannot_delete_newly_referenced_media(unverified_worker, tmp_path):
    _, worker = unverified_worker
    with override_settings(MEDIA_ROOT=tmp_path):
        name = "workers/photos/still-used.png"
        path = tmp_path / name
        path.parent.mkdir(parents=True)
        path.write_bytes(b"Synthetic file")
        worker.photo.name = name
        worker.save(update_fields=["photo"])
        task = MediaDeletionTask.objects.create(name=name)
        assert process_media_erasure()["completed"] == 1 and path.exists()
        task.refresh_from_db()
        assert task.error_code == "referenced_media_preserved"


@pytest.mark.django_db
def test_media_retry_command_reports_storage_failure_with_nonzero_status(tmp_path):
    MediaDeletionTask.objects.create(name="workers/photos/synthetic.png")
    with override_settings(MEDIA_ROOT=tmp_path), \
         patch("apps.common.media_erasure.default_storage.delete", side_effect=OSError("private-path")):
        with pytest.raises(CommandError, match="tasks remain pending"):
            call_command("retry_media_erasure", apply=True, confirm_media_root=str(tmp_path), stdout=StringIO())
    assert MediaDeletionTask.objects.get().completed_at is None


def test_static_build_settings_cannot_be_selected_as_production_fallback():
    env = {**os.environ, "ISHCHI_ENV": "production", "DJANGO_SETTINGS_MODULE": "config.settings.build"}
    result = subprocess.run([sys.executable, "-c", "from django.conf import settings; print(settings.DEBUG)"],
        cwd=ROOT / "backend", env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "cannot run in production mode" in result.stderr


def test_redis_integration_fixture_releases_clients_without_flush():
    """Exercise the real fixture teardown and django-redis close logic offline."""
    from redistests.test_redis import redis_cache
    with patch("redistests.test_redis.authorize_redis"), patch("apps.common.redis_backend.authorize_redis"), \
         patch.dict(os.environ, {"REDIS_URL": "rediss://synthetic:synthetic@cache.invalid:6379/15"}):
        fixture = redis_cache.__wrapped__()
        cache = next(fixture)
        client = cache.client  # Construction is lazy and does not open a socket.
        acquired_client = object()  # An acquired client, never a real connection.
        client._clients[0] = acquired_client
        with patch.object(cache, "delete_pattern") as cleanup, patch.object(client.connection_factory, "disconnect") as disconnect:
            fixture.close()
        cleanup.assert_called_once_with("*")
        disconnect.assert_called_once_with(acquired_client)
        assert client._clients == [None]
