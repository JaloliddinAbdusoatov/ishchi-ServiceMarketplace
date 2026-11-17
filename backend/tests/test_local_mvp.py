"""Offline local-MVP gates. Never starts or connects PostgreSQL/Redis services."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest
import yaml
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings

from apps.common.local_targets import validate_local_pg, validate_local_redis
from apps.common.redis_backend import RedisCache, redis_target
from apps.common.db_backends.postgresql.base import DatabaseWrapper

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local_mvp_cli", ROOT / "deploy/local.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)

WORK = {"host": "postgres-work", "port": "5432", "dbname": "ishchi_marketplace_local", "user": "ishchi_local_app"}
TEST = {"host": "127.0.0.1", "port": "55433", "dbname": "ishchi_marketplace_sprint1_local", "user": "ishchi_local_test"}


@pytest.mark.parametrize("target,kind", [(WORK, "test"), (TEST, "work"), ({**WORK, "dbname": "ishchi_test"}, "work"),
    ({**TEST, "port": "55432"}, "test"), ({**TEST, "user": "ishchi_bootstrap"}, "test")])
def test_local_database_targets_never_cross_work_test_boundary(target, kind):
    with pytest.raises(ImproperlyConfigured):
        validate_local_pg(target, kind)


def test_local_targets_match_fixed_services():
    validate_local_pg(WORK, "work")
    validate_local_pg(TEST, "test")
    validate_local_redis({"host": "127.0.0.1", "port": 56380, "database": 0, "user": "ishchi_local_test"}, "test")


def test_plaintext_redis_is_only_accepted_in_deliberate_exact_local_context():
    url = "redis://ishchi_local_app:synthetic-secret@127.0.0.1:56379/0"
    with pytest.raises(ImproperlyConfigured):
        redis_target(url)
    target = redis_target(url, allow_local=True)
    validate_local_redis(target, "work")
    with pytest.raises(ImproperlyConfigured):
        validate_local_redis(target, "test")
    with override_settings(LOCAL_TARGET_KIND="test"):
        cache = RedisCache(url, {})
        with patch.object(cache, "_client_cls") as client:
            with pytest.raises(ImproperlyConfigured, match="Local Redis"):
                cache.get("synthetic")
            client.assert_not_called()


def test_local_flags_never_open_production_connections():
    with override_settings(IS_PRODUCTION=True, LOCAL_TARGET_KIND="work", POSTGRES_INTEGRATION=True), patch(
        "django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection"
    ) as driver:
        with pytest.raises(ImproperlyConfigured, match="Production database access is blocked"):
            DatabaseWrapper({}).get_new_connection(WORK)
        with pytest.raises(ImproperlyConfigured, match="Production Redis access is blocked"):
            RedisCache("redis://ishchi_local_app:synthetic-secret@redis-work:6379/0", {}).get("synthetic")
        driver.assert_not_called()


def test_persistent_migrations_require_separate_scope_before_database_access(tmp_path, monkeypatch):
    document = {"target": WORK, "approved_by": "Synthetic unit input", "expires_at": "2099-01-01T00:00:00Z",
                "operations": ["connect"], "disposable": False}
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(document))
    monkeypatch.setenv("DB_AUTHORIZATION_FILE", str(path))
    with override_settings(LOCAL_TARGET_KIND="work"), patch.object(connection, "get_connection_params", return_value=WORK), patch.object(connection, "cursor") as cursor:
        with pytest.raises(CommandError, match="migration operator"):
            call_command("migrate", skip_checks=True)
        cursor.assert_not_called()


def test_local_secret_generation_never_approves_or_overwrites_targets(tmp_path):
    folder = local.initialize_secrets(tmp_path / "private")
    assert len({(folder / name).read_text() for name in local.SECRET_NAMES}) == len(local.SECRET_NAMES)
    for path in folder.glob("*-authorization.json"):
        document = json.loads(path.read_text())
        assert document["approved_by"] == "" and document["expires_at"].startswith("2000-")
    with pytest.raises(ValueError, match="overwrite"):
        local.initialize_secrets(folder)


def test_local_test_launcher_cannot_inherit_working_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_NAME", "ishchi_marketplace_local")
    monkeypatch.setenv("PGPASSWORD", "synthetic-working-password")
    monkeypatch.setenv("REDIS_URL", "redis://synthetic@redis-work/0")
    for kind in ("pg", "redis"):
        command, env = local.test_command(kind, tmp_path)
        assert "DB_NAME" not in env and "PGPASSWORD" not in env and "REDIS_URL" not in env
        assert Path(env["DB_PASSWORD_FILE"]).name == "test_pg_password"
        assert Path(env["REDIS_PASSWORD_FILE"]).name == "test_redis_password"
        assert command[-2].endswith("_integration_local")


@pytest.mark.parametrize("fault", ["public-port", "shared-volume", "shared-network", "production", "auto-profile", "database", "external-volume", "auto-migrate", "internal-network"])
def test_local_compose_check_rejects_unsafe_boundaries(tmp_path, fault):
    document = local.check()
    services = document["services"]
    if fault == "public-port":
        services["backend"]["ports"] = ["8080:8080"]
    elif fault == "shared-volume":
        services["postgres-test"]["volumes"][0] = "pg-work:/var/lib/postgresql"
    elif fault == "shared-network":
        services["redis-test"]["networks"] = ["work"]
    elif fault == "production":
        services["backend"]["environment"]["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    elif fault == "auto-profile":
        services["backend"]["profiles"] = []
    elif fault == "database":
        services["postgres-test"]["environment"]["POSTGRES_DB"] = "ishchi_marketplace_local"
    elif fault == "external-volume":
        document["volumes"]["pg-work"] = {"external": True}
    elif fault == "auto-migrate":
        services["backend"]["command"] = ["python", "manage.py", "migrate"]
    else:
        document["networks"]["test"]["internal"] = True
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy/compose.local.yml").write_text(yaml.safe_dump(document))
    with pytest.raises(ValueError):
        local.check(tmp_path)


@pytest.mark.parametrize("production", [False, True])
@pytest.mark.parametrize("module", ["local_postgres", "local_migration"])
def test_local_settings_load_without_sockets_and_cannot_be_production_fallback(tmp_path, production, module):
    directory = local.initialize_secrets(tmp_path / "private")
    env = {key: value for key, value in os.environ.items() if not key.startswith(("DB_", "REDIS_", "DJANGO_", "ISHCHI_", "PG"))}
    env.update(DJANGO_SETTINGS_MODULE="config.settings." + module, ISHCHI_ENV="production" if production else "local",
        DJANGO_SECRET_KEY_FILE=str(directory / "django_key"), DB_PASSWORD_FILE=str(directory / "work_pg_password"),
        REDIS_PASSWORD_FILE=str(directory / "work_redis_password"))
    result = subprocess.run([sys.executable, "-c", """
import socket
def denied(*args, **kwargs): raise AssertionError('Network attempted')
socket.socket.connect = denied
import django
from unittest.mock import patch
with patch('django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection', side_effect=denied):
    django.setup()
    from django.conf import settings
    assert not settings.DEBUG and not settings.IS_PRODUCTION
    assert settings.DATABASES['default']['NAME'] == 'ishchi_marketplace_local'
    assert settings.DATABASES['default']['ENGINE'] == 'apps.common.db_backends.postgresql'
    if settings.LOCAL_TARGET_KIND == 'migration':
        assert settings.DATABASES['default']['USER'] == 'ishchi_local_migrator'
        assert settings.DATABASES['default']['OPTIONS']['assume_role'] == 'ishchi_local_owner'
    else:
        assert settings.DATABASES['default']['USER'] == 'ishchi_local_app'
        assert 'assume_role' not in settings.DATABASES['default']['OPTIONS']
    assert settings.CACHES['default']['LOCATION'].startswith('redis://ishchi_local_app:')
    assert settings.SMS_BACKEND == 'disabled' and not settings.PAYMENT_ENABLED
    from django.core.management import call_command
    call_command('check')
"""], cwd=ROOT / "backend", env=env, capture_output=True, text=True, timeout=20)
    assert (result.returncode != 0) == production, result.stderr


def test_local_backup_and_restore_plans_remain_inert_and_disjoint(tmp_path):
    backup = local.recovery_plan("backup", tmp_path, recipient="age1" + "a" * 58)
    restore = local.recovery_plan("restore", None, archive=tmp_path / "ishchi-database-20261116T000000Z-1234abcd.dump.age", identity_file=tmp_path / "key")
    assert backup["target"]["database"] == "ishchi_marketplace_local"
    assert restore["target"]["database"] == "ishchi_marketplace_restore_local"
    assert backup["target"]["port"] == 55432 and restore["target"]["port"] == 55434
    assert backup["execution"].startswith("BLOCKED") and restore["execution"].startswith("BLOCKED")
    assert not list(tmp_path.iterdir())


def test_smoke_cleanup_stops_owned_interpreter_tree_and_releases_files(tmp_path):
    smoke_spec = importlib.util.spec_from_file_location("local_smoke_cleanup", ROOT / "deploy/smoke_local.py")
    smoke = importlib.util.module_from_spec(smoke_spec)
    smoke_spec.loader.exec_module(smoke)
    path = tmp_path / "synthetic-child.log"
    child = subprocess.Popen([sys.executable, "-c",
        "import sys,time; f=open(sys.argv[1],'w'); f.write('ready'); f.flush(); time.sleep(30)", str(path)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 5
        while not path.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert path.exists()
    finally:
        smoke.stop_child(child)
    assert child.poll() is not None
    path.unlink()  # Windows refuses this if a venv redirector left its child alive.
    assert not path.exists()
