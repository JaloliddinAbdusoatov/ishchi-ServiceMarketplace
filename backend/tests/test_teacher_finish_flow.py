"""Real SQLite ORM/API integration: no PostgreSQL, Redis, or external SMS."""
from unittest.mock import patch

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services.auth_service import AuthService
from apps.applications.models import OrderApplication
from apps.common.exceptions import BusinessRuleViolation
from apps.categories.models import WorkerCategory
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile
from tests.conftest import CategoryFactory

pytestmark = pytest.mark.django_db


def registered_client(phone, role):
    client = APIClient()
    with patch("apps.accounts.services.otp_service.get_sms_provider") as provider:
        result = client.post("/api/v1/auth/register/", {
            "phone_number": phone, "password": "DemoFlow2026!",
            "full_name": f"Synthetic {role}", "role": role, "location": "Toshkent",
        }, format="json")
        assert result.status_code == 201, result.data
        provider.assert_not_called()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.data['data']['tokens']['access']}")
    user = User.objects.get(phone_number=phone)
    assert user.is_active and not user.is_phone_verified and user.account_status == "ACTIVE"
    return client, user


def apply(client, order_id):
    return client.post("/api/v1/applications/", {
        "order": str(order_id), "cover_message": "Synthetic worker is available", "proposed_price": "100000.00",
    }, format="json")


def test_registered_unverified_team_to_chat_completion_reviews_and_admin(active_category):
    employer, owner = registered_client("+998935500001", "EMPLOYER")
    worker, user = registered_client("+998935500002", "WORKER")
    second, second_user = registered_client("+998935500003", "WORKER")
    stranger, stranger_user = registered_client("+998935500004", "WORKER")
    assert not user.worker_profile.is_verified
    profile = worker.patch("/api/v1/profiles/worker/", {"bio": "Synthetic teacher demo worker", "location": "Toshkent"}, format="json")
    assert profile.status_code == 200, profile.data
    categories = worker.put("/api/v1/profiles/worker/categories/", {"categories": [{"category_id": str(active_category.id), "is_primary": True}]}, format="json")
    assert categories.status_code == 200, categories.data
    created = employer.post("/api/v1/orders/", {
        "category": str(active_category.id), "title": "Synthetic team job", "description": "Two workers for a teacher demo",
        "budget": "200000.00", "location": "Toshkent", "status": "PUBLISHED", "capacity": 2,
    }, format="json")
    assert created.status_code == 201, created.data
    order_id = str(created.data["data"]["id"])
    assert APIClient().get("/api/v1/orders/").status_code == 200
    one, two, other = apply(worker, order_id), apply(second, order_id), apply(stranger, order_id)
    assert [one.status_code, two.status_code, other.status_code] == [201, 201, 201]
    assert apply(worker, order_id).status_code == 409
    for app in (one, two):
        accepted = employer.post(f"/api/v1/applications/{app.data['data']['id']}/accept/")
        assert accepted.status_code == 200, accepted.data
    order = ServiceOrder.objects.get(pk=order_id)
    assert order.capacity == 2 and order.assigned_workers.count() == 2 and order.status == "IN_PROGRESS"
    assert employer.post(f"/api/v1/applications/{other.data['data']['id']}/accept/").status_code >= 400
    assert stranger.post("/api/v1/chat/conversations/", {"order": order_id}, format="json").status_code == 403
    conversation = second.post("/api/v1/chat/conversations/", {"order": order_id}, format="json")
    assert conversation.status_code in (200, 201), conversation.data
    conv_id = conversation.data["data"]["id"]
    for client in (employer, second):
        sent = client.post(f"/api/v1/chat/conversations/{conv_id}/messages/", {"content": "Synthetic work update"}, format="json")
        assert sent.status_code == 201, sent.data
    assert stranger.get(f"/api/v1/chat/conversations/{conv_id}/messages/").status_code == 403
    assert second.get(f"/api/v1/chat/conversations/{conv_id}/messages/").data["count"] == 2
    assert employer.post("/api/v1/reviews/", {"order": order_id, "rating": 5}, format="json").status_code == 400
    assert employer.post(f"/api/v1/orders/{order_id}/complete/").status_code == 200
    for target in (user, second_user):
        response = employer.post("/api/v1/reviews/", {"order": order_id, "rating": 5, "reviewee": str(target.id)}, format="json")
        assert response.status_code == 201, response.data
        assert employer.post("/api/v1/reviews/", {"order": order_id, "rating": 5, "reviewee": str(target.id)}, format="json").status_code == 409
    assert second.post("/api/v1/reviews/", {"order": order_id, "rating": 4}, format="json").status_code == 201
    assert stranger.post("/api/v1/reviews/", {"order": order_id, "rating": 1}, format="json").status_code == 403
    second_user.worker_profile.refresh_from_db()
    assert second_user.worker_profile.review_count == 1
    assert second.get("/api/v1/orders/?assigned_to_me=true").data["count"] == 1
    assert second.get("/api/v1/notifications/").data["count"] >= 3
    assert worker.get("/api/v1/admin/dashboard/").status_code == 403
    admin = User.objects.create_superuser(phone_number="+998935500005", password="DemoFlow2026!", full_name="Synthetic admin")
    admin_client = APIClient()
    admin_client.force_authenticate(admin)
    metrics = admin_client.get("/api/v1/admin/dashboard/")
    assert metrics.status_code == 200, metrics.data
    assert metrics.data["data"]["reviews_total"] == 3
    assert metrics.data["data"]["applications_total"] == 3
    assert metrics.data["data"]["orders"]["by_status"]["COMPLETED"] == 1


def test_invitation_alone_never_grants_chat(auth_client, employer_pair, unverified_worker, published_order):
    owner, _ = employer_pair
    user, worker = unverified_worker
    invitation = auth_client(owner).post("/api/v1/invitations/", {"order": str(published_order.id), "worker": str(worker.id)}, format="json")
    assert invitation.status_code == 201, invitation.data
    for client, body in ((auth_client(user), {"order": str(published_order.id)}), (auth_client(owner), {"order": str(published_order.id), "worker": str(worker.id)})):
        assert client.post("/api/v1/chat/conversations/", body, format="json").status_code == 403
    assert auth_client(user).post(f"/api/v1/invitations/{invitation.data['data']['id']}/accept/").status_code == 200
    assert auth_client(user).post("/api/v1/chat/conversations/", {"order": str(published_order.id)}, format="json").status_code == 403


def test_category_limits_are_enforced_by_api_and_sqlite(auth_client, unverified_worker):
    user, worker = unverified_worker
    cats = [CategoryFactory() for _ in range(11)]
    payload = {"categories": [{"category_id": str(c.id), "is_primary": False} for c in cats]}
    assert auth_client(user).put("/api/v1/profiles/worker/categories/", payload, format="json").status_code == 400
    payload["categories"].pop()
    assert auth_client(user).put("/api/v1/profiles/worker/categories/", payload, format="json").status_code == 200
    with pytest.raises(IntegrityError), transaction.atomic():
        WorkerCategory.objects.create(worker=worker, category=cats[-1])
    cats[0].is_active = False
    cats[0].save(update_fields=["is_active"])
    assert WorkerCategory.objects.filter(worker=worker).count() == 9


def test_local_runtime_is_sqlite_only_and_health_works(client):
    assert connection.vendor == "sqlite"
    assert "ishchi_test" not in str(connection.settings_dict["NAME"])
    result = client.get("/api/v1/health/")
    assert result.status_code == 200
    assert result.json()["redis"] == {"status": "ok"}


def test_partial_team_rejects_double_hiring_across_application_and_invitation(auth_client, employer_pair, unverified_worker, published_order):
    owner, _ = employer_pair
    user, worker = unverified_worker
    published_order.capacity = 2
    published_order.save(update_fields=["capacity"])
    employer, applicant = auth_client(owner), auth_client(user)
    invitation = employer.post("/api/v1/invitations/", {"order": str(published_order.id), "worker": str(worker.id)}, format="json")
    application = apply(applicant, published_order.id)
    assert employer.post(f"/api/v1/applications/{application.data['data']['id']}/accept/").status_code == 200
    assert applicant.post(f"/api/v1/invitations/{invitation.data['data']['id']}/accept/").status_code == 409
    published_order.refresh_from_db()
    assert published_order.hired_worker_count == 1 and published_order.status == "PUBLISHED"
    with pytest.raises(BusinessRuleViolation, match="active order"):
        AuthService.anonymize_and_delete_account(user, password="StrongPass2026!")
    user.refresh_from_db()
    assert not user.is_anonymized


@pytest.mark.parametrize("change", ["withdrawn", "worker_suspended", "employer_suspended"])
def test_chat_revokes_messages_and_previews_after_participation_ends(auth_client, employer_pair, unverified_worker, published_order, change):
    owner, _ = employer_pair
    user, worker = unverified_worker
    employer, applicant = auth_client(owner), auth_client(user)
    application = apply(applicant, published_order.id)
    assert application.status_code == 201
    conversation = applicant.post("/api/v1/chat/conversations/", {"order": str(published_order.id)}, format="json")
    conversation_id = conversation.data["data"]["id"]
    assert applicant.post(f"/api/v1/chat/conversations/{conversation_id}/messages/", {"content": "Synthetic private message"}, format="json").status_code == 201
    if change == "withdrawn":
        OrderApplication.objects.filter(pk=application.data["data"]["id"]).update(status="WITHDRAWN")
        viewer = employer
    elif change == "worker_suspended":
        User.objects.filter(pk=user.pk).update(account_status="SUSPENDED")
        viewer = employer
    else:
        User.objects.filter(pk=owner.pk).update(account_status="SUSPENDED")
        viewer = applicant
    assert viewer.get("/api/v1/chat/conversations/").data["count"] == 0
    assert viewer.get(f"/api/v1/chat/conversations/{conversation_id}/messages/").status_code == 403
    assert viewer.post(f"/api/v1/chat/conversations/{conversation_id}/messages/", {"content": "Blocked"}, format="json").status_code == 403


@pytest.mark.parametrize("capacity", [0, 51])
def test_capacity_bounds(auth_client, employer_pair, active_category, capacity):
    owner, _ = employer_pair
    response = auth_client(owner).post("/api/v1/orders/", {
        "category": str(active_category.id), "title": "Synthetic invalid capacity", "description": "Synthetic data only",
        "budget": "1000", "location": "Toshkent", "capacity": capacity,
    }, format="json")
    assert response.status_code == 400
