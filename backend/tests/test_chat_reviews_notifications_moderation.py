from decimal import Decimal
import pytest
from rest_framework import status

from apps.accounts.models import AccountDeletionAudit, AccountStatus, User, UserRole
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.chat.models import Conversation, Message
from apps.orders.models import OrderStatus, ServiceOrder
from apps.profiles.models import EmployerProfile, VerificationStatus, WorkerProfile
from apps.reviews.models import Review
from tests.conftest import UserFactory


@pytest.mark.django_db
class TestChatReviewsModerationAnonymization:
    def test_chat_strict_authorization_and_messaging(
        self, auth_client, employer_pair, verified_worker, unverified_worker, published_order
    ):
        e_user, e_profile = employer_pair
        w_user, w_profile = verified_worker
        other_user, _ = unverified_worker

        e_client = auth_client(e_user)
        w_client = auth_client(w_user)
        other_client = auth_client(other_user)

        # Worker who has NOT applied cannot open chat
        denied_open = w_client.post(
            "/api/v1/chat/conversations/",
            {"order": str(published_order.id)},
            format="json",
        )
        assert denied_open.status_code == status.HTTP_403_FORBIDDEN

        # Worker submits application -> now allowed to open chat
        app_resp = w_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Ishga tayyorman", "proposed_price": "450000.00"},
            format="json",
        )
        assert app_resp.status_code == status.HTTP_201_CREATED

        conv_resp = w_client.post(
            "/api/v1/chat/conversations/",
            {"order": str(published_order.id)},
            format="json",
        )
        assert conv_resp.status_code == status.HTTP_201_CREATED
        conv_id = conv_resp.data["data"]["id"]

        # Send message from worker -> employer
        msg_resp = w_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages/",
            {"content": "Assalomu alaykum, ertaga boshlaymizmi?"},
            format="json",
        )
        assert msg_resp.status_code == status.HTTP_201_CREATED

        # Unrelated user guessing conversation ID gets 403
        intruder_read = other_client.get(f"/api/v1/chat/conversations/{conv_id}/messages/")
        assert intruder_read.status_code == status.HTTP_403_FORBIDDEN
        intruder_send = other_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages/",
            {"content": "Hacked message"},
            format="json",
        )
        assert intruder_send.status_code == status.HTTP_403_FORBIDDEN

        # Employer reads and marks read
        emp_msgs = e_client.get(f"/api/v1/chat/conversations/{conv_id}/messages/")
        assert emp_msgs.status_code == status.HTTP_200_OK
        assert emp_msgs.data["count"] == 1

        mark_read = e_client.post(f"/api/v1/chat/conversations/{conv_id}/read/")
        assert mark_read.status_code == status.HTTP_200_OK
        assert mark_read.data["data"]["marked_read_count"] == 1

    def test_bidirectional_reviews_and_rating_updates(
        self, auth_client, employer_pair, verified_worker, unverified_worker, published_order
    ):
        e_user, e_profile = employer_pair
        w_user, w_profile = verified_worker
        outsider_user, _ = unverified_worker

        e_client = auth_client(e_user)
        w_client = auth_client(w_user)
        outsider_client = auth_client(outsider_user)

        # Cannot review before order is COMPLETED
        early = e_client.post(
            "/api/v1/reviews/",
            {"order": str(published_order.id), "rating": 5, "comment": "Too early"},
            format="json",
        )
        assert early.status_code == status.HTTP_400_BAD_REQUEST

        # Apply -> Accept -> Complete
        app_resp = w_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Bajaraman", "proposed_price": "500000.00"},
            format="json",
        )
        app_id = app_resp.data["data"]["id"]
        e_client.post(f"/api/v1/applications/{app_id}/accept/")
        comp = e_client.post(f"/api/v1/orders/{published_order.id}/complete/")
        assert comp.status_code == status.HTTP_200_OK

        # Outsider cannot review
        outsider_rev = outsider_client.post(
            "/api/v1/reviews/",
            {"order": str(published_order.id), "rating": 1, "comment": "Fake review"},
            format="json",
        )
        assert outsider_rev.status_code == status.HTTP_403_FORBIDDEN

        # Employer reviews worker
        r1 = e_client.post(
            "/api/v1/reviews/",
            {"order": str(published_order.id), "rating": 5, "comment": "A'lo darajada!"},
            format="json",
        )
        assert r1.status_code == status.HTTP_201_CREATED
        assert r1.data["data"]["direction"] == "EMPLOYER_TO_WORKER"

        # Duplicate review in same direction blocked
        r1_dup = e_client.post(
            "/api/v1/reviews/",
            {"order": str(published_order.id), "rating": 4, "comment": "Duplicate"},
            format="json",
        )
        assert r1_dup.status_code == status.HTTP_409_CONFLICT

        # Worker reviews employer
        r2 = w_client.post(
            "/api/v1/reviews/",
            {"order": str(published_order.id), "rating": 4, "comment": "Yaxshi buyurtmachi"},
            format="json",
        )
        assert r2.status_code == status.HTTP_201_CREATED
        assert r2.data["data"]["direction"] == "WORKER_TO_EMPLOYER"

        w_profile.refresh_from_db()
        e_profile.refresh_from_db()
        assert w_profile.rating_avg == Decimal("5.00")
        assert w_profile.review_count == 1
        assert e_profile.rating_avg == Decimal("4.00")
        assert e_profile.review_count == 1

    def test_notifications_favorites_reports_and_admin_dashboard(
        self, auth_client, admin_user, employer_pair, verified_worker, published_order
    ):
        e_user, _ = employer_pair
        w_user, w_profile = verified_worker
        e_client = auth_client(e_user)
        w_client = auth_client(w_user)
        a_client = auth_client(admin_user)

        # Favorite worker & order
        assert e_client.post("/api/v1/favorites/workers/", {"worker": str(w_profile.id)}, format="json").status_code == 201
        assert w_client.post("/api/v1/favorites/orders/", {"order": str(published_order.id)}, format="json").status_code == 201

        # Report order
        rep = w_client.post(
            "/api/v1/reports/",
            {
                "target_type": "ORDER",
                "target_id": str(published_order.id),
                "reason": "SPAM",
                "description": "Shubhali e'lon matni",
            },
            format="json",
        )
        assert rep.status_code == status.HTTP_201_CREATED
        report_id = rep.data["data"]["id"]

        # Ordinary user blocked from admin endpoints
        assert w_client.get("/api/v1/admin/dashboard/").status_code == status.HTTP_403_FORBIDDEN
        assert w_client.post(f"/api/v1/admin/reports/{report_id}/resolve/", {"status": "RESOLVED"}, format="json").status_code == 403

        # Admin resolves report & accesses dashboard
        res = a_client.post(
            f"/api/v1/admin/reports/{report_id}/resolve/",
            {"status": "RESOLVED", "admin_resolution": "Tekshirildi va yopildi"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["data"]["status"] == "RESOLVED"

        dash = a_client.get("/api/v1/admin/dashboard/")
        assert dash.status_code == status.HTTP_200_OK
        assert dash.data["data"]["users"]["total"] >= 3

        # Admin suspends worker -> worker tokens immediately fail
        susp = a_client.post(f"/api/v1/admin/users/{w_user.id}/suspend/", {"reason": "Policy violation"}, format="json")
        assert susp.status_code == status.HTTP_200_OK
        assert w_client.get("/api/v1/auth/me/").status_code == status.HTTP_401_UNAUTHORIZED

        # Reactivate
        act = a_client.post(f"/api/v1/admin/users/{w_user.id}/activate/")
        assert act.status_code == status.HTTP_200_OK

    def test_account_deletion_anonymizes_pii_and_preserves_history(
        self, auth_client, employer_pair, verified_worker, published_order
    ):
        e_user, e_profile = employer_pair
        w_user, w_profile = verified_worker
        e_client = auth_client(e_user)
        w_client = auth_client(w_user)

        # Complete an order first so transaction history exists
        app_resp = w_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Ishni bajaraman", "proposed_price": "500000.00"},
            format="json",
        )
        app_id = app_resp.data["data"]["id"]
        e_client.post(f"/api/v1/applications/{app_id}/accept/")
        e_client.post(f"/api/v1/orders/{published_order.id}/complete/")

        old_phone = w_user.phone_number

        # Delete & anonymize worker account
        del_resp = w_client.post(
            "/api/v1/auth/delete-account/",
            {"password": "StrongPass2026!", "confirm": True, "reason": "No longer needed"},
            format="json",
        )
        assert del_resp.status_code == status.HTTP_200_OK

        w_user.refresh_from_db()
        w_profile.refresh_from_db()
        assert w_user.is_anonymized is True
        assert w_user.phone_number is None
        assert w_user.email is None
        assert w_user.is_active is False
        assert w_user.account_status == AccountStatus.DELETED
        assert w_profile.full_name.startswith("Deleted Worker")
        assert w_profile.is_verified is False

        # Audit record exists
        assert AccountDeletionAudit.objects.filter(user_id=w_user.id).exists()

        # Preserves completed order history
        published_order.refresh_from_db()
        assert published_order.status == OrderStatus.COMPLETED
        assert published_order.assigned_worker_id == w_profile.id

        # Old JWT token immediately rejected
        assert w_client.get("/api/v1/auth/me/").status_code == status.HTTP_401_UNAUTHORIZED

        # Old credentials cannot login
        login_retry = auth_client(e_user)
        login_retry.credentials()
        bad_login = login_retry.post(
            "/api/v1/auth/login/",
            {"phone_number": old_phone, "password": "StrongPass2026!"},
            format="json",
        )
        assert bad_login.status_code == status.HTTP_401_UNAUTHORIZED

    def test_system_health_payment_disabled_and_openapi_docs(self, api_client):
        health = api_client.get("/api/v1/health/")
        assert health.status_code == status.HTTP_200_OK
        assert health.data["database"]["status"] == "ok"
        assert health.data["redis"]["status"] == "ok"
        assert health.data["payments_enabled"] is False

        pay = api_client.get("/api/v1/payments/status/")
        assert pay.status_code == status.HTTP_200_OK
        assert pay.data["data"]["enabled"] is False
        assert pay.data["data"]["status"] == "DISABLED"

        schema = api_client.get("/api/schema/")
        assert schema.status_code == status.HTTP_404_NOT_FOUND
        docs = api_client.get("/api/docs/")
        assert docs.status_code == status.HTTP_404_NOT_FOUND
