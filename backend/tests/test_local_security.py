"""Rotation procedure regressions on ephemeral SQLite, never the working account."""
from io import StringIO
import importlib.util
from pathlib import Path
from unittest.mock import patch
import uuid

import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import User
from apps.accounts.services.auth_service import generate_jwt_pair
from apps.accounts.services.local_security import rotate_local_admin_password
from tests.conftest import UserFactory

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.django_db
def test_single_admin_rotation_revokes_old_jwts_preserves_other_accounts_and_data(admin_user, api_client, published_order):
    from django.conf import settings
    from apps.orders.models import ServiceOrder
    other = UserFactory()
    old = generate_jwt_pair(admin_user)
    second = generate_jwt_pair(admin_user)
    other_tokens = generate_jwt_pair(other)
    operator_browser = Client()
    operator_browser.force_login(admin_user)
    assert operator_browser.get("/django-admin/").status_code == 200
    old_key = settings.SECRET_KEY
    prior = list(ServiceOrder.objects.values())
    count = User.objects.count()
    with override_settings(LOCAL_TARGET_KIND="work"):
        rotate_local_admin_password(admin_user.pk, "RotatedLocalAccount2026!")
    admin_user.refresh_from_db()
    other.refresh_from_db()
    assert admin_user.token_version == 2 and other.token_version == 1
    assert admin_user.check_password("RotatedLocalAccount2026!")
    assert User.objects.count() == count and list(ServiceOrder.objects.values()) == prior
    assert settings.SECRET_KEY == old_key
    assert operator_browser.get("/django-admin/").status_code == 302
    assert operator_browser.login(phone_number=admin_user.phone_number, password="RotatedLocalAccount2026!")
    assert operator_browser.get("/django-admin/").status_code == 200
    assert BlacklistedToken.objects.filter(token__user=admin_user).count() == 2
    for tokens in (old, second):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        assert api_client.get("/api/v1/admin/dashboard/").status_code == 401
        api_client.credentials()
        assert api_client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401
    assert api_client.post("/api/v1/auth/login/", {"phone_number": admin_user.phone_number, "password": "AdminPass2026!"}, format="json").status_code == 401
    result = api_client.post("/api/v1/auth/login/", {"phone_number": admin_user.phone_number, "password": "RotatedLocalAccount2026!"}, format="json")
    assert result.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION="Bearer " + result.data["data"]["tokens"]["access"])
    assert api_client.get("/api/v1/admin/dashboard/").status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION="Bearer " + other_tokens["access"])
    assert api_client.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_rotation_and_revocation_roll_back_together_on_failure(admin_user):
    generate_jwt_pair(admin_user)
    password_hash = admin_user.password
    version = admin_user.token_version
    with override_settings(LOCAL_TARGET_KIND="work"), patch(
        "apps.accounts.services.local_security._blacklist_all_user_tokens", side_effect=RuntimeError("Induced revocation failure")
    ), pytest.raises(RuntimeError, match="Induced"):
        rotate_local_admin_password(admin_user.pk, "RotatedLocalAccount2026!")
    admin_user.refresh_from_db()
    assert admin_user.password == password_hash and admin_user.token_version == version
    assert not BlacklistedToken.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["non-admin", "inactive", "same-password", "weak-password"])
def test_rotation_rejects_wrong_subject_or_unsafe_password(admin_user, kind):
    subject = UserFactory() if kind == "non-admin" else admin_user
    if kind == "inactive":
        subject.is_active = False
        subject.save(update_fields=["is_active"])
    original = subject.password
    password = {"same-password": "AdminPass2026!", "weak-password": "short"}.get(kind, "RotatedLocalAccount2026!")
    with override_settings(LOCAL_TARGET_KIND="work"), pytest.raises(ValidationError):
        rotate_local_admin_password(subject.pk, password)
    subject.refresh_from_db()
    assert subject.password == original and subject.token_version == 1


@pytest.mark.parametrize("production,kind", [(True, "work"), (False, "test"), (False, "")])
def test_rotation_context_blocks_before_account_lookup(production, kind):
    with override_settings(IS_PRODUCTION=production, LOCAL_TARGET_KIND=kind), patch(
        "apps.accounts.services.local_security.User.objects.select_for_update"
    ) as lookup, pytest.raises(ImproperlyConfigured):
        rotate_local_admin_password(uuid.uuid4(), "NotEnteredIntoARealAccount2026!")
    lookup.assert_not_called()


def test_rotation_command_dry_run_never_reads_or_mutates_an_account():
    output = StringIO()
    with override_settings(LOCAL_TARGET_KIND="work"), patch("django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection", side_effect=AssertionError("Connection attempted")):
        call_command("rotate_local_admin", account=uuid.uuid4(), stdout=output)
    assert "DRY RUN" in output.getvalue()


def test_rotation_command_rejects_piped_passwords_before_lookup():
    with override_settings(LOCAL_TARGET_KIND="work"), patch("sys.stdin.isatty", return_value=False), patch(
        "apps.accounts.management.commands.rotate_local_admin.getpass.getpass"
    ) as prompt, pytest.raises(CommandError, match="interactive"):
        call_command("rotate_local_admin", account=uuid.uuid4(), apply=True)
    prompt.assert_not_called()


@pytest.mark.django_db
def test_interactive_command_retries_mismatch_and_weak_input_without_exposing_passwords(admin_user):
    output, errors = StringIO(), StringIO()
    fresh = "FreshHiddenRotation2026!"
    entries = ["AdminPass2026!", fresh, "mismatched", "q7!T", "q7!T", fresh, fresh]
    with override_settings(LOCAL_TARGET_KIND="work"), patch("sys.stdin.isatty", return_value=True), patch(
        "apps.accounts.management.commands.rotate_local_admin.getpass.getpass", side_effect=entries
    ):
        call_command("rotate_local_admin", account=admin_user.pk, apply=True, verify=True, stdout=output, stderr=errors)
    admin_user.refresh_from_db()
    assert admin_user.check_password(fresh) and admin_user.token_version == 2
    assert "did not match" in errors.getvalue() and "Password rejected" in errors.getvalue()
    assert "old password/access/refresh/admin session rejected" in output.getvalue()
    for password in entries:
        assert password not in output.getvalue() + errors.getvalue()


@pytest.mark.django_db
def test_failed_interactive_entries_create_no_verification_sessions_or_account_changes(admin_user):
    from django.contrib.sessions.models import Session
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    original = (admin_user.password, admin_user.last_login, admin_user.token_version)
    entries = ["AdminPass2026!"] + ["short", "short"] * 3
    with override_settings(LOCAL_TARGET_KIND="work"), patch("sys.stdin.isatty", return_value=True), patch(
        "apps.accounts.management.commands.rotate_local_admin.getpass.getpass", side_effect=entries
    ), pytest.raises(CommandError, match="Three unsuccessful"):
        call_command("rotate_local_admin", account=admin_user.pk, apply=True, verify=True, stderr=StringIO())
    admin_user.refresh_from_db()
    assert (admin_user.password, admin_user.last_login, admin_user.token_version) == original
    assert not Session.objects.exists() and not OutstandingToken.objects.exists()


@pytest.mark.django_db
def test_owner_approved_reset_without_previous_password_verifies_revocation_and_reports_missing_check(admin_user):
    output = StringIO()
    fresh = "UnknownPreviousFresh2026!"
    with override_settings(LOCAL_TARGET_KIND="work"), patch("sys.stdin.isatty", return_value=True), patch(
        "apps.accounts.management.commands.rotate_local_admin.getpass.getpass", side_effect=[fresh, fresh]
    ) as prompts:
        call_command("rotate_local_admin", account=admin_user.pk, apply=True, previous_password_unknown=True, stdout=output)
    admin_user.refresh_from_db()
    assert admin_user.check_password(fresh) and admin_user.token_version == 2
    assert prompts.call_count == 2
    assert all("Previous" not in c.args[0] for c in prompts.call_args_list)
    assert "PASS: old access/refresh/admin session rejected" in output.getvalue()
    assert "NOT RUN: old-password login rejection" in output.getvalue()
    assert fresh not in output.getvalue()


def test_retired_verifier_never_reads_plaintext_credentials_or_bootstraps(tmp_path):
    spec = importlib.util.spec_from_file_location("retired_local_verifier", ROOT / "deploy/verify_local.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    with patch.object(Path, "read_text", side_effect=AssertionError("Credential read attempted")), patch.object(
        verifier, "verify"
    ) as run, pytest.raises(SystemExit) as exit_result:
        verifier.main(["--credentials", str(tmp_path / "exposed.json"), "--bootstrap-admin"])
    assert exit_result.value.code == 2
    run.assert_not_called()
