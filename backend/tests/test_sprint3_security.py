"""Real SQLite/API regressions; no PostgreSQL or Redis integration claims."""
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountDeletionAudit, User
from apps.accounts.services.auth_service import AuthService, generate_jwt_pair
from apps.accounts.services.otp_service import OTPPurpose, OTPService
from apps.accounts.services.sms_service import SMSUnavailable
from apps.applications.models import OrderApplication
from apps.chat.services import ChatService
from apps.favorites.models import FavoriteOrder
from apps.invitations.models import OrderInvitation
from apps.notifications.models import Notification
from apps.orders.models import ServiceOrder
from apps.reports.models import Report
from tests.conftest import UserFactory

pytestmark = pytest.mark.django_db


def send_code(user, purpose=OTPPurpose.VERIFY_PHONE):
    with patch("apps.accounts.services.otp_service.get_sms_provider") as provider:
        assert OTPService.send_otp(user.phone_number, purpose=purpose)["success"]
    return provider.return_value.send_otp.call_args.args[1]


def test_phone_verification_never_logs_into_a_preclaimed_account(api_client, auth_client, unverified_worker):
    user, _ = unverified_worker
    code = send_code(user)
    payload = {"phone_number": user.phone_number, "otp": code}
    assert api_client.post("/api/v1/auth/otp/verify/", payload).status_code == 401
    stranger = auth_client(UserFactory())
    assert stranger.post("/api/v1/auth/otp/verify/", payload).status_code == 403
    assert stranger.post("/api/v1/auth/otp/send/", {"phone_number": user.phone_number}).status_code == 403
    response = auth_client(user).post("/api/v1/auth/otp/verify/", payload)
    assert response.status_code == 200
    assert "tokens" not in response.data["data"]
    assert response.data["data"]["user"]["is_phone_verified"] is True
    assert auth_client(user).post("/api/v1/auth/otp/verify/", payload).status_code == 400


@pytest.mark.parametrize("path", ["otp/send/", "password/reset/request/"])
def test_reset_responses_do_not_reveal_account_or_cooldown(api_client, path):
    known = UserFactory(is_phone_verified=True)
    unknown = "+998935566700"
    payload = {"phone_number": known.phone_number, "purpose": "PASSWORD_RESET"}
    with patch("apps.accounts.services.otp_service.get_sms_provider"):
        first = api_client.post("/api/v1/auth/" + path, payload).data
        cooldown = api_client.post("/api/v1/auth/" + path, payload).data
        absent = api_client.post("/api/v1/auth/" + path, {**payload, "phone_number": unknown}).data
    assert first == cooldown == absent
    with patch("apps.accounts.services.otp_service.get_sms_provider", side_effect=SMSUnavailable):
        cache.clear()
        failed = api_client.post("/api/v1/auth/" + path, payload)
    assert failed.status_code == 200 and failed.data == absent
    assert cache.get(f"otp_session:PASSWORD_RESET:{known.phone_number}") is None


def test_reset_cannot_trust_an_unverified_registration_number(api_client):
    user = UserFactory(is_phone_verified=False)
    with patch("apps.accounts.services.otp_service.get_sms_provider") as provider:
        assert api_client.post("/api/v1/auth/password/reset/request/", {"phone_number": user.phone_number}).status_code == 200
        provider.assert_not_called()
    # Even a code generated through a lower-level call cannot bypass eligibility.
    code = send_code(user, OTPPurpose.PASSWORD_RESET)
    response = api_client.post("/api/v1/auth/password/reset/confirm/", {
        "phone_number": user.phone_number, "otp": code, "new_password": "DifferentPassword2026!"})
    assert response.status_code == 400
    user.refresh_from_db()
    assert not user.check_password("DifferentPassword2026!")


def test_reset_is_single_use_and_revokes_all_existing_sessions(api_client):
    user = UserFactory(is_phone_verified=True)
    old = generate_jwt_pair(user)
    code = send_code(user, OTPPurpose.PASSWORD_RESET)
    payload = {"phone_number": user.phone_number, "otp": code, "new_password": "DifferentPassword2026!"}
    assert api_client.post("/api/v1/auth/password/reset/confirm/", payload).status_code == 200
    assert api_client.post("/api/v1/auth/password/reset/confirm/", payload).status_code == 400
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old['access']}")
    assert api_client.get("/api/v1/auth/me/").status_code == 401
    assert api_client.post("/api/v1/auth/token/refresh/", {"refresh": old["refresh"]}).status_code == 401


@pytest.mark.parametrize("mutation", ["version", "replacement"])
def test_otp_cannot_outlive_account_or_credential_identity(mutation):
    user = UserFactory(is_phone_verified=True)
    phone = user.phone_number
    code = send_code(user, OTPPurpose.PASSWORD_RESET)
    if mutation == "version":
        AuthService.logout_all_sessions(user)
    else:
        AuthService.anonymize_and_delete_account(user, require_password=False)
        UserFactory(phone_number=phone, is_phone_verified=True)
    assert OTPService.verify_otp(phone, code, purpose=OTPPurpose.PASSWORD_RESET)[0] is False


def test_failed_password_validation_does_not_consume_reset_code(api_client):
    user = UserFactory(is_phone_verified=True)
    code = send_code(user, OTPPurpose.PASSWORD_RESET)
    payload = {"phone_number": user.phone_number, "otp": code, "new_password": "12345678"}
    assert api_client.post("/api/v1/auth/password/reset/confirm/", payload).status_code == 400
    payload["new_password"] = "DifferentPassword2026!"
    assert api_client.post("/api/v1/auth/password/reset/confirm/", payload).status_code == 200


@pytest.mark.parametrize("path,payload", [
    ("register/", {"phone_number": "+998935566704", "password": "StrongRegistration2026!", "full_name": "Rate Limit User"}),
    ("login/", {"phone_number": "+998935566701", "password": "WrongPassword!"}),
    ("token/refresh/", {"refresh": "invalid"}),
    ("password/reset/confirm/", {"phone_number": "+998935566701", "otp": "000000", "new_password": "DifferentPassword2026!"}),
])
def test_forwarded_headers_cannot_bypass_auth_throttling(api_client, settings, path, payload):
    rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "auth": "2/min"}
    from apps.accounts.throttling import SecurityScopedThrottle
    with patch.object(SecurityScopedThrottle, "THROTTLE_RATES", rates):
        for index in range(2):
            assert api_client.post("/api/v1/auth/" + path, payload,
                HTTP_X_FORWARDED_FOR=f"198.51.100.{index}", HTTP_X_REAL_IP=f"198.51.100.{index}").status_code != 429
        assert api_client.post("/api/v1/auth/" + path, payload,
            HTTP_X_FORWARDED_FOR="198.51.100.99", HTTP_X_REAL_IP="198.51.100.99").status_code == 429


@pytest.mark.parametrize("known", [True, False])
def test_reset_cache_outage_is_sanitized_for_all_accounts(api_client, known):
    phone = UserFactory(is_phone_verified=True).phone_number if known else "+998935566702"
    with patch("apps.accounts.services.auth_service.cache.get", side_effect=RedisConnectionError("private-secret")):
        response = api_client.post("/api/v1/auth/password/reset/request/", {"phone_number": phone})
    assert response.status_code == 503 and "private-secret" not in str(response.data)


def test_password_whitespace_is_preserved(api_client):
    password = "  StrongWhitespace2026!  "
    payload = {"phone_number": "+998935566703", "password": password, "full_name": "Whitespace User"}
    assert api_client.post("/api/v1/auth/register/", payload).status_code == 201
    assert api_client.post("/api/v1/auth/login/", payload).status_code == 200
    assert api_client.post("/api/v1/auth/login/", {**payload, "password": password.strip()}).status_code == 401


@pytest.mark.parametrize("endpoint", [
    "dashboard/", "users/", "users/{user}/suspend/", "users/{user}/activate/",
    "workers/", "workers/{worker}/verify/", "orders/", "orders/{order}/moderate/",
    "reports/", "reports/{user}/resolve/",
])
def test_every_admin_api_rejects_regular_users(auth_client, unverified_worker, published_order, endpoint):
    user, worker = unverified_worker
    url = "/api/v1/admin/" + endpoint.format(user=user.pk, worker=worker.pk, order=published_order.pk)
    client = auth_client(user)
    method = client.post if any(word in url for word in ("suspend", "activate", "verify", "moderate", "resolve")) else client.get
    assert method(url, {}, format="json").status_code == 403
    assert not LogEntry.objects.exists()


@pytest.mark.parametrize("model", [User, AccountDeletionAudit, LogEntry])
def test_operator_admin_forms_cannot_bypass_service_or_edit_audits(admin_user, model):
    model_admin = admin.site._registry[model]
    request = SimpleNamespace(user=admin_user)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)


def test_kyc_notes_are_visible_only_to_owner_and_admin(auth_client, api_client, admin_user, unverified_worker, employer_pair):
    user, worker = unverified_worker
    worker.verification_notes = "Private KYC reviewer note"
    worker.save(update_fields=["verification_notes"])
    url = f"/api/v1/workers/{worker.pk}/"
    for client in (api_client, auth_client(employer_pair[0])):
        assert client.get(url).data["data"]["verification_notes"] == ""
    for actor in (user, admin_user):
        assert auth_client(actor).get(url).data["data"]["verification_notes"] == worker.verification_notes


def test_private_orders_cannot_leak_through_favorites(auth_client, unverified_worker, published_order):
    client = auth_client(unverified_worker[0])
    url = "/api/v1/favorites/orders/"
    assert client.post(url, {"order": str(published_order.pk)}).status_code == 201
    published_order.status = "DRAFT"
    published_order.save(update_fields=["status"])
    assert client.get(url).data["results"] == []
    assert client.post(url, {"order": str(published_order.pk)}).status_code == 404
    assert FavoriteOrder.objects.count() == 1  # Bookmark never grants visibility.


def test_suspended_employer_order_detail_is_private(auth_client, employer_pair, unverified_worker, published_order):
    owner, _ = employer_pair
    owner.account_status = "SUSPENDED"
    owner.save(update_fields=["account_status"])
    assert auth_client(unverified_worker[0]).get(f"/api/v1/orders/{published_order.pk}/").status_code == 403


def test_private_objects_cannot_be_reported_by_strangers(auth_client, unverified_worker, published_order):
    user, worker = unverified_worker
    OrderApplication.objects.create(order=published_order, worker=worker, proposed_price=100)
    conv, _ = ChatService.get_or_create_conversation(user, published_order.pk)
    message = ChatService.send_message(conv, user, content="Private conversation")
    client = auth_client(UserFactory())
    payload = {"target_type": "MESSAGE", "target_id": str(message.pk), "reason": "SPAM", "description": "Private target"}
    assert client.post("/api/v1/reports/", payload).status_code == 403
    published_order.status = "DRAFT"
    published_order.save(update_fields=["status"])
    payload.update(target_type="ORDER", target_id=str(published_order.pk))
    assert client.post("/api/v1/reports/", payload).status_code == 404
    assert not Report.objects.exists()


@pytest.mark.parametrize("action", ["accept", "reject", "withdraw"])
def test_strangers_cannot_modify_or_hire_applications(auth_client, unverified_worker, employer_pair, published_order, action):
    row = OrderApplication.objects.create(order=published_order, worker=unverified_worker[1], proposed_price=100)
    user = UserFactory(role="EMPLOYER" if action != "withdraw" else "WORKER")
    from apps.profiles.models import EmployerProfile, WorkerProfile
    (EmployerProfile if action != "withdraw" else WorkerProfile).objects.create(user=user, full_name="Stranger")
    assert auth_client(user).post(f"/api/v1/applications/{row.pk}/{action}/").status_code == 403
    row.refresh_from_db()
    assert row.status == "PENDING" and published_order.assigned_workers.count() == 0


@pytest.mark.parametrize("action", ["accept", "reject", "cancel"])
def test_strangers_cannot_modify_invitations(auth_client, unverified_worker, employer_pair, published_order, action):
    row = OrderInvitation.objects.create(order=published_order, employer=employer_pair[1], worker=unverified_worker[1],
        expires_at=timezone.now() + timedelta(days=1))
    user = UserFactory(role="EMPLOYER" if action == "cancel" else "WORKER")
    from apps.profiles.models import EmployerProfile, WorkerProfile
    (EmployerProfile if action == "cancel" else WorkerProfile).objects.create(user=user, full_name="Stranger")
    assert auth_client(user).post(f"/api/v1/invitations/{row.pk}/{action}/").status_code == 403
    row.refresh_from_db()
    assert row.status == "PENDING"


def test_notification_read_delete_and_list_are_isolated(auth_client, unverified_worker, employer_pair):
    owner = unverified_worker[0]
    notification = Notification.objects.create(recipient=owner, event_type="NEW_MESSAGE", title="Private", message="Private")
    client = auth_client(employer_pair[0])
    assert client.get("/api/v1/notifications/").data["results"] == []
    assert client.post(f"/api/v1/notifications/{notification.pk}/read/").status_code == 404
    assert client.delete(f"/api/v1/notifications/{notification.pk}/").status_code == 404
    client.post("/api/v1/notifications/read-all/")
    notification.refresh_from_db()
    assert not notification.is_read


@pytest.mark.parametrize("name,content,mime", [
    ("payload.pdf", b"<script>alert(1)</script>", "application/pdf"),
    ("payload.doc", b"Not an OLE document", "application/msword"),
    ("payload.docx", b"Not a ZIP document", "application/octet-stream"),
    ("payload.txt", b"binary\x00data", "text/plain"),
    ("payload.txt", b"safe text", "text/html"),
    ("payload.svg", b"<svg/>", "image/svg+xml"),
])
def test_unsafe_attachments_are_rejected_before_storage(auth_client, unverified_worker, published_order, tmp_path, name, content, mime):
    user, worker = unverified_worker
    OrderApplication.objects.create(order=published_order, worker=worker, proposed_price=100)
    conversation, _ = ChatService.get_or_create_conversation(user, published_order.pk)
    with override_settings(MEDIA_ROOT=tmp_path):
        response = auth_client(user).post(f"/api/v1/chat/conversations/{conversation.pk}/messages/",
            {"attachment": SimpleUploadedFile(name, content, content_type=mime)}, format="multipart")
    assert response.status_code == 400
    assert not conversation.messages.exists() and not list(tmp_path.rglob("*"))


def test_docx_archive_cannot_contain_traversal():
    from apps.common.validators import validate_chat_attachment
    from django.core.exceptions import ValidationError
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name in ("[Content_Types].xml", "word/document.xml", "../payload"):
            archive.writestr(name, "data")
    with pytest.raises(ValidationError):
        validate_chat_attachment(SimpleUploadedFile("payload.docx", buffer.getvalue(), content_type="application/octet-stream"))


def test_admin_mutation_and_audit_commit_or_rollback_together(auth_client, admin_user, unverified_worker):
    user, _ = unverified_worker
    client = auth_client(admin_user)
    url = f"/api/v1/admin/users/{user.pk}/suspend/"
    tokens = generate_jwt_pair(user)
    with patch("apps.accounts.services.audit_service.LogEntry.objects.create", side_effect=RuntimeError("private-error")):
        response = client.post(url)
    assert response.status_code == 500 and "private-error" not in str(response.data)
    user.refresh_from_db()
    assert user.is_active and user.token_version == 1 and not LogEntry.objects.exists()
    assert client.post(url).status_code == 200
    audit = LogEntry.objects.get()
    assert audit.user_id == admin_user.pk and audit.object_id == str(user.pk)
    assert audit.change_message == "account.suspended" and user.phone_number not in audit.object_repr
    assert APIClient().post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code == 401
    assert client.post(f"/api/v1/admin/users/{user.pk}/activate/").status_code == 200
    assert LogEntry.objects.count() == 2


def test_deletion_audit_failure_rolls_back_anonymization_and_tokens(auth_client, unverified_worker):
    user, worker = unverified_worker
    client = auth_client(user)
    with patch("apps.accounts.services.auth_service.AccountDeletionAudit.objects.create", side_effect=RuntimeError("audit failure")):
        with pytest.raises(RuntimeError):
            AuthService.anonymize_and_delete_account(user, require_password=False)
    user.refresh_from_db()
    worker.refresh_from_db()
    assert not user.is_anonymized and worker.full_name == user.full_name
    assert client.get("/api/v1/auth/me/").status_code == 200
    audit = AuthService.anonymize_and_delete_account(user, require_password=False, reason=user.phone_number)
    assert not audit.reason and user.phone_number not in str(audit.__dict__)
    assert client.get("/api/v1/auth/me/").status_code == 401


def test_auth_logs_do_not_include_password_or_tokens(api_client, caplog):
    user = UserFactory()
    secret = "NeverLogThisPassword2026!"
    api_client.post("/api/v1/auth/login/", {"phone_number": user.phone_number, "password": secret})
    tokens = generate_jwt_pair(user)
    api_client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]})
    assert secret not in caplog.text and tokens["refresh"] not in caplog.text and tokens["access"] not in caplog.text


def test_order_images_obey_current_order_visibility_and_block_static_urls(auth_client, api_client, published_order, employer_pair, tmp_path):
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    owner = auth_client(employer_pair[0])
    upload_url = f"/api/v1/orders/{published_order.pk}/images/"
    with override_settings(MEDIA_ROOT=tmp_path):
        upload = owner.post(upload_url, {"image": SimpleUploadedFile("private.png", buffer.getvalue(), content_type="image/png")}, format="multipart")
        assert upload.status_code == 201
        url = upload.data["data"]["image"]
        assert url.startswith("/api/v1/orders/") and "/media/" not in url
        public = api_client.get(url)
        assert public.status_code == 200
        assert b"".join(public.streaming_content) == buffer.getvalue()
        public.close()
        image = published_order.images.get()
        assert api_client.get("/media/" + image.image.name).status_code == 404
        published_order.status = "DRAFT"
        published_order.save(update_fields=["status"])
        assert api_client.get(url).status_code == 404
        assert auth_client(UserFactory()).get(url).status_code == 404
        response = owner.get(url)
        assert response.status_code == 200 and response["Cache-Control"] == "private, no-store"
        response.close()


def test_category_change_and_audit_roll_back_together(auth_client, admin_user, active_category):
    client = auth_client(admin_user)
    url = f"/api/v1/categories/{active_category.pk}/"
    original = active_category.name
    with patch("apps.accounts.services.audit_service.LogEntry.objects.create", side_effect=RuntimeError("audit failure")):
        assert client.patch(url, {"name": "New name"}).status_code == 500
    active_category.refresh_from_db()
    assert active_category.name == original and not LogEntry.objects.exists()
    assert client.patch(url, {"name": "New name"}).status_code == 200
    assert LogEntry.objects.get().change_message == "category.updated"


def test_kyc_moderation_audits_without_copying_private_notes(auth_client, admin_user, unverified_worker):
    user, worker = unverified_worker
    client = auth_client(admin_user)
    response = client.post(f"/api/v1/admin/workers/{worker.pk}/verify/", {
        "action": "APPROVE", "notes": "Private identity document notes"})
    assert response.status_code == 200
    entry = LogEntry.objects.get()
    assert entry.change_message == "worker.verification.approve"
    assert "Private identity" not in str(entry.__dict__)
    assert entry.object_id == str(worker.pk) and entry.user_id == admin_user.pk


def test_moderation_closes_pending_requests_and_audits_atomically(auth_client, admin_user, unverified_worker, employer_pair, published_order):
    worker = unverified_worker[1]
    application = OrderApplication.objects.create(order=published_order, worker=worker, proposed_price=100)
    invitation = OrderInvitation.objects.create(order=published_order, employer=employer_pair[1], worker=worker,
        expires_at=timezone.now() + timedelta(days=1))
    client = auth_client(admin_user)
    url = f"/api/v1/admin/orders/{published_order.pk}/moderate/"
    with patch("apps.accounts.services.audit_service.LogEntry.objects.create", side_effect=RuntimeError("audit failure")):
        assert client.post(url, {"action": "CANCEL"}).status_code == 500
    for row in (published_order, application, invitation):
        row.refresh_from_db()
    assert published_order.status == "PUBLISHED" and application.status == invitation.status == "PENDING"
    assert not Notification.objects.exists() and not LogEntry.objects.exists()
    assert client.post(url, {"action": "CANCEL"}).status_code == 200
    application.refresh_from_db()
    invitation.refresh_from_db()
    assert application.status == "REJECTED" and invitation.status == "CANCELLED"
    assert LogEntry.objects.get().change_message == "order.moderation.cancel"


def test_public_profile_media_is_erased_after_successful_anonymization(unverified_worker, tmp_path, django_capture_on_commit_callbacks):
    from PIL import Image
    from apps.profiles.models import WorkerPortfolioItem
    user, worker = unverified_worker
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    with override_settings(MEDIA_ROOT=tmp_path):
        worker.photo.save("profile.png", SimpleUploadedFile("profile.png", buffer.getvalue()), save=True)
        item = WorkerPortfolioItem.objects.create(worker=worker, title="Old portfolio",
            image=SimpleUploadedFile("portfolio.png", buffer.getvalue()))
        names = [worker.photo.name, item.image.name]
        storage = worker.photo.storage
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            with patch("apps.accounts.services.auth_service.AccountDeletionAudit.objects.create", side_effect=RuntimeError("audit failure")):
                with pytest.raises(RuntimeError):
                    AuthService.anonymize_and_delete_account(user, require_password=False)
        assert not callbacks and all(storage.exists(name) for name in names)
        with django_capture_on_commit_callbacks(execute=True):
            AuthService.anonymize_and_delete_account(user, require_password=False)
        assert all(not storage.exists(name) for name in names)


def test_applications_cannot_target_suspended_employers(auth_client, unverified_worker, employer_pair, published_order):
    user, _ = employer_pair
    user.account_status = "SUSPENDED"
    user.save(update_fields=["account_status"])
    response = auth_client(unverified_worker[0]).post("/api/v1/applications/", {
        "order": str(published_order.pk), "cover_message": "Ready to work", "proposed_price": "100"})
    assert response.status_code == 403
    assert not OrderApplication.objects.exists() and not Notification.objects.exists()


def test_django_operator_ui_requires_admin_role_not_only_staff():
    user = UserFactory(is_staff=True, role="WORKER")
    request = SimpleNamespace(user=user)
    assert not admin.site.has_permission(request)
    user.role = "ADMIN"
    assert admin.site.has_permission(request)
    user.account_status = "SUSPENDED"
    assert not admin.site.has_permission(request)


def test_django_admin_login_throttles_spoofed_forwarding_headers():
    from django.test import Client
    client = Client()
    for index in range(10):
        response = client.post("/django-admin/login/", {"username": "+998935566799", "password": "WrongPassword!"},
            HTTP_X_FORWARDED_FOR=f"198.51.100.{index}")
        assert response.status_code == 200
    assert client.post("/django-admin/login/", {}, HTTP_X_FORWARDED_FOR="198.51.100.99").status_code == 429


def test_django_admin_login_fails_closed_on_cache_outage():
    from django.test import Client
    with patch("apps.accounts.admin_site.increment_bucket", side_effect=RedisConnectionError("private-secret")):
        response = Client().post("/django-admin/login/", {})
    assert response.status_code == 503 and b"private-secret" not in response.content
