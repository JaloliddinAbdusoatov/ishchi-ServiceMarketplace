"""Offline configuration and migration-graph checks. No PostgreSQL sockets."""
import json
import importlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db.migrations.loader import MigrationLoader

from apps.common.db_authorization import authorize
from apps.common.db_backends.postgresql.base import DatabaseWrapper
from config.settings.database import postgres_database
from tests.test_production_mvp import production_environment


def test_migration_graph_has_no_conflicts_or_missing_dependencies():
    loader = MigrationLoader(None)
    loader.graph.validate_consistency()
    loader.graph.ensure_not_cyclic()
    assert loader.detect_conflicts() == {}
    state = loader.project_state()
    assert state.apps.get_model("orders", "ServiceOrder")._meta.get_field("assigned_workers")


def test_postgres_trigger_sql_keeps_literal_percent_signs():
    loader = MigrationLoader(None)
    editor = MagicMock()
    editor.connection.vendor = "postgresql"
    category = importlib.import_module("apps.categories.migrations.0002_category_integrity_triggers")
    category.install_triggers(None, editor)
    editor.execute.assert_called_once_with(category.TRIGGER_SQL, params=None)
    editor.reset_mock()
    hiring = importlib.import_module("apps.orders.migrations.0004_postgres_hiring_integrity")
    hiring.install(loader.project_state().apps, editor)
    assert editor.execute.call_args_list[0].kwargs == {"params": None}


def test_unapproved_redis_cannot_instantiate_client(monkeypatch):
    from apps.common.redis_backend import RedisCache
    monkeypatch.delenv("REDIS_AUTHORIZATION_FILE", raising=False)
    cache = RedisCache("rediss://default:synthetic@cache.invalid:6379/1", {})
    with patch.object(cache, "_client_cls") as client:
        with pytest.raises(ImproperlyConfigured, match="Explicit"):
            cache.get("synthetic")
        client.assert_not_called()


@pytest.mark.parametrize("override", [
    {"DB_NAME": ""}, {"DB_USER": ""}, {"DB_PASSWORD": ""}, {"DB_HOST": ""},
    {"DB_NAME": "ishchi_test"}, {"DB_SSLMODE": "require"}, {"DB_SSLMODE": "disable"},
    {"DB_SSLROOTCERT": "missing-file"}, {"DB_PORT": "bad"}, {"DB_PORT": "0"},
    {"DB_CONNECT_TIMEOUT": "0"}, {"DB_CONN_MAX_AGE": "-1"},
])
def test_production_database_fails_closed(override):
    with pytest.raises(ImproperlyConfigured):
        postgres_database({**production_environment(), **override}, production=True)


def test_connection_lifetime_timeout_and_tls_are_configurable():
    config = postgres_database({**production_environment(), "DB_CONN_MAX_AGE": "120", "DB_CONNECT_TIMEOUT": "9"}, production=True)
    assert config["CONN_MAX_AGE"] == 120
    assert config["OPTIONS"]["connect_timeout"] == 9
    assert config["OPTIONS"]["sslmode"] == "verify-full"
    assert config["ENGINE"] == "apps.common.db_backends.postgresql"


def test_missing_authorization_blocks_driver_before_socket(monkeypatch):
    monkeypatch.delenv("DB_AUTHORIZATION_FILE", raising=False)
    with patch("django.db.backends.postgresql.base.DatabaseWrapper.get_new_connection") as driver:
        with pytest.raises(ImproperlyConfigured, match="Explicit"):
            DatabaseWrapper({}).get_new_connection({"dbname": "ishchi_marketplace_sprint1_offline", "host": "db.invalid", "port": "5432", "user": "runtime"})
        driver.assert_not_called()


@pytest.mark.parametrize("change", ["target", "expired", "scope", "disposable", "missing_approver", "malformed_operations"])
def test_authorization_must_cover_exact_target_and_operation(tmp_path, monkeypatch, change):
    target = {"dbname": "ishchi_marketplace_sprint1_offline", "host": "db.invalid", "port": "5432", "user": "runtime"}
    document = {"target": target.copy(), "approved_by": "Synthetic offline test", "disposable": True,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "operations": ["connect", "test_schema"]}
    if change == "target":
        document["target"]["host"] = "other.invalid"
    elif change == "expired":
        document["expires_at"] = "2000-01-01T00:00:00Z"
    elif change == "scope":
        document["operations"] = ["connect"]
    elif change == "disposable":
        document["disposable"] = False
    elif change == "malformed_operations":
        document["operations"] = "connect test_schema"
    else:
        document["approved_by"] = ""
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(document))
    monkeypatch.setenv("DB_AUTHORIZATION_FILE", str(path))
    with pytest.raises(ImproperlyConfigured):
        authorize(target, "test_schema")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["application", "invitation"])
@pytest.mark.parametrize("actor", ["worker", "employer"])
def test_hiring_rechecks_current_account_state(employer_pair, unverified_worker, published_order, path, actor):
    from apps.accounts.models import User
    from apps.applications.services import ApplicationService
    from apps.common.exceptions import ForbiddenActionError
    from apps.invitations.services import InvitationService
    owner, employer = employer_pair
    user, worker = unverified_worker
    application = ApplicationService.submit_application(worker, published_order.pk, "Synthetic", 100)
    invitation = InvitationService.send_invitation(employer, published_order.pk, worker.pk)
    # Keep original in-memory objects deliberately stale.
    User.objects.filter(pk=(user if actor == "worker" else owner).pk).update(account_status="SUSPENDED")
    with pytest.raises(ForbiddenActionError):
        if path == "application":
            ApplicationService.accept_application(application.pk, employer)
        else:
            InvitationService.accept_invitation(invitation.pk, worker)
    application.refresh_from_db()
    invitation.refresh_from_db()
    published_order.refresh_from_db()
    assert application.status == "PENDING" and invitation.status == "PENDING"
    assert published_order.hired_worker_count == 0
