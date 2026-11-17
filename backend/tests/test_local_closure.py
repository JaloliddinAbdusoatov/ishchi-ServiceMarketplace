"""Offline closure checks: ephemeral SQLite and SQL generation, no local PG access."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from apps.common.local_targets import validate_local_pg
from apps.common.db_backends.postgresql.base import DatabaseWrapper

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("role,kind,allowed", [
    ("ishchi_local_migrator", "migration", True),
    ("ishchi_local_app", "migration", False),
    ("ishchi_local_migrator", "work", False),
    ("ishchi_bootstrap", "migration", False),
])
def test_migration_login_has_its_own_exact_target(role, kind, allowed):
    target = dict(host="127.0.0.1", port="55432", dbname="ishchi_marketplace_local", user=role)
    if allowed:
        validate_local_pg(target, kind)
    else:
        with pytest.raises(ImproperlyConfigured):
            validate_local_pg(target, kind)


def test_runtime_schema_editor_denies_before_connection_or_approval_file():
    with override_settings(LOCAL_TARGET_KIND="work"), patch.object(DatabaseWrapper, "get_connection_params") as params:
        with pytest.raises(ImproperlyConfigured, match="migration operator"):
            DatabaseWrapper({}).schema_editor()
        params.assert_not_called()


def test_audit_probe_dry_run_never_connects():
    with patch("django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection", side_effect=AssertionError("Connection attempted")):
        call_command("verify_local_audit_privileges")


def test_audit_probe_rejects_non_postgresql_context_before_query():
    from apps.accounts.management.commands.verify_local_audit_privileges import preflight
    with override_settings(LOCAL_TARGET_KIND="work"), pytest.raises(CommandError, match="PostgreSQL"):
        preflight()


def test_marketplace_probe_defaults_to_no_database_and_rejects_sqlite_execution():
    from apps.accounts.management.commands.verify_local_marketplace import exercise
    with patch("django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection", side_effect=AssertionError("Connection attempted")):
        call_command("verify_local_marketplace")
    with override_settings(LOCAL_TARGET_KIND="work"), pytest.raises(CommandError, match="PostgreSQL"):
        exercise()


def test_migration_operator_requires_separate_scope_before_schema_editor():
    target = dict(host="127.0.0.1", port="55432", dbname="ishchi_marketplace_local", user="ishchi_local_migrator")
    with override_settings(LOCAL_TARGET_KIND="migration"), patch.object(DatabaseWrapper, "get_connection_params", return_value=target), patch(
        "apps.common.db_authorization.authorize", side_effect=ImproperlyConfigured("Missing local_migrate scope")
    ) as approval:
        with pytest.raises(ImproperlyConfigured, match="local_migrate"):
            DatabaseWrapper({}).schema_editor()
        approval.assert_called_once_with(target, "local_migrate")


def test_generated_policy_and_checked_in_sql_match_without_execution():
    spec = importlib.util.spec_from_file_location("privilege_policy", ROOT / "deploy/local_privileges.py")
    plan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plan)
    for name in ("accounts_deletion_audit", "django_admin_log"):
        assert plan.POLICY[name] == "SELECT, INSERT"
    assert plan.POLICY["django_migrations"] == "SELECT"
    for filename, generated in (("apply.sql", plan.apply_sql()), ("rollback.sql", plan.rollback_sql())):
        assert (ROOT / "deploy/local/privileges" / filename).read_text() == generated
        assert "current_database() <> 'ishchi_marketplace_local'" in generated
        assert "session_user <> 'ishchi_bootstrap'" in generated
        assert "DROP " not in generated and "TRUNCATE " not in generated
    assert "WITH ADMIN FALSE, INHERIT FALSE, SET TRUE" in plan.apply_sql()
    assert "PASSWORD NULL" in plan.apply_sql()


def test_privileged_operator_defaults_to_no_connection_no_secret_generation():
    spec = importlib.util.spec_from_file_location("local_role_operator", ROOT / "deploy/apply_local_roles.py")
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    with patch.object(operator, "approval", side_effect=AssertionError("Approval read attempted")), patch.object(
        operator.secrets, "token_urlsafe", side_effect=AssertionError("Secret generated")
    ), patch.object(operator.subprocess, "run", side_effect=AssertionError("Command attempted")):
        operator.main([])


def test_local_recovery_default_does_not_read_approval_generate_keys_or_connect():
    spec = importlib.util.spec_from_file_location("local_recovery_operator", ROOT / "deploy/local_recovery.py")
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    with patch.object(operator, "require_approval", side_effect=AssertionError("Approval read attempted")), patch.object(
        operator.subprocess, "run", side_effect=AssertionError("Command attempted")
    ):
        operator.main([])


def test_recovery_index_normalization_is_limited_to_exact_known_cast_rewrite():
    spec = importlib.util.spec_from_file_location("local_recovery_index", ROOT / "deploy/local_recovery.py")
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    old="WHERE ((status)::text = ANY ((ARRAY['PENDING'::character varying, 'ACCEPTED'::character varying])::text[]))"
    new="WHERE ((status)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('ACCEPTED'::character varying)::text]))"
    assert recovery.canonical_index_definition('uq_active_order_worker_application',old)==new
    assert recovery.canonical_index_definition('other_index',old)==old
    changed=old.replace('ACCEPTED','WITHDRAWN')
    assert recovery.canonical_index_definition('uq_active_order_worker_application',changed)==changed


@pytest.mark.django_db
def test_interactive_rotation_verification_checks_real_auth_paths_on_sqlite(admin_user):
    from apps.accounts.services.local_rotation_verification import prepare_verification
    from apps.accounts.services.local_security import rotate_local_admin_password
    with override_settings(LOCAL_TARGET_KIND="work"):
        verify = prepare_verification(admin_user.pk, "AdminPass2026!")
        rotate_local_admin_password(admin_user.pk, "NewLocalClosure2026!password")
        verify("NewLocalClosure2026!password")


@pytest.mark.django_db
def test_verification_refuses_wrong_previous_password_before_session_creation(admin_user):
    from apps.accounts.services.local_rotation_verification import prepare_verification
    with override_settings(LOCAL_TARGET_KIND="work"), patch("django.test.Client.force_login") as session:
        with pytest.raises(CommandError, match="Previous"):
            prepare_verification(admin_user.pk, "incorrect")
        session.assert_not_called()
