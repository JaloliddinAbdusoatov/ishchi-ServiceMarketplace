from datetime import timedelta
from decimal import Decimal
import threading
import pytest
from django.db import connections
from django.utils import timezone
from rest_framework import status

from apps.applications.models import ApplicationStatus, OrderApplication
from apps.applications.services import ApplicationService
from apps.common.exceptions import BusinessRuleViolation, ConflictError
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.invitations.services import InvitationService
from apps.orders.models import BudgetType, OrderStatus, ServiceOrder, WorkType
from apps.profiles.models import EmployerProfile, EmployerType, VerificationStatus, WorkerProfile
from tests.conftest import UserFactory


@pytest.mark.django_db
class TestOrdersApplicationsInvitations:
    def test_employer_order_lifecycle_and_filtering(self, auth_client, employer_pair, active_category):
        emp_user, _ = employer_pair
        client = auth_client(emp_user)

        create_resp = client.post(
            "/api/v1/orders/",
            {
                "category": str(active_category.id),
                "title": "Elektr montaj",
                "description": "3 xonali uy elektr simlarini almashtirish",
                "budget": "1500000.00",
                "budget_type": "FIXED",
                "location": "Toshkent",
                "district": "Yunusobod",
                "work_type": "ONSITE",
                "status": "DRAFT",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        order_id = create_resp.data["data"]["id"]
        assert create_resp.data["data"]["status"] == "DRAFT"
        assert create_resp.data["data"]["payment_status"] == "DISABLED"

        # Publish
        pub = client.post(f"/api/v1/orders/{order_id}/publish/")
        assert pub.status_code == status.HTTP_200_OK
        assert pub.data["data"]["status"] == "PUBLISHED"

        # Pause
        pause = client.post(f"/api/v1/orders/{order_id}/pause/")
        assert pause.status_code == status.HTTP_200_OK
        assert pause.data["data"]["status"] == "PAUSED"

        # Republish and search/filter
        client.post(f"/api/v1/orders/{order_id}/publish/")
        list_resp = client.get("/api/v1/orders/?location=Toshkent&budget_min=1000000&search=Elektr")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.data["count"] >= 1

    def test_unverified_and_verified_workers_can_apply_and_prevent_duplicates(
        self, auth_client, verified_worker, unverified_worker, published_order
    ):
        unver_user, unver_profile = unverified_worker
        ver_user, ver_profile = verified_worker

        # Batch 16 (PDR-PRODUCT-14 / Option A): Unverified worker can apply successfully
        r_unver = auth_client(unver_user).post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Ishni qilaman", "proposed_price": "450000.00"},
            format="json",
        )
        assert r_unver.status_code == status.HTTP_201_CREATED

        # Duplicate active application prevented for unverified worker as well
        r_dup_unver = auth_client(unver_user).post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Yana ariza", "proposed_price": "470000.00"},
            format="json",
        )
        assert r_dup_unver.status_code == status.HTTP_409_CONFLICT

        # Verified worker also succeeds on their own application
        ver_client = auth_client(ver_user)
        r_ver = ver_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Tajribam bor", "proposed_price": "480000.00"},
            format="json",
        )
        assert r_ver.status_code == status.HTTP_201_CREATED

        # Duplicate active application prevented
        r_dup = ver_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Yana ariza", "proposed_price": "470000.00"},
            format="json",
        )
        assert r_dup.status_code == status.HTTP_409_CONFLICT

    def test_worker_cannot_apply_to_own_order(self, auth_client, verified_worker, active_category):
        user, worker_profile = verified_worker
        # Enable employer role on same user
        emp_profile = EmployerProfile.objects.create(
            user=user,
            employer_type=EmployerType.INDIVIDUAL,
            full_name=user.full_name,
            phone_number=user.phone_number,
        )
        user.has_employer_role = True
        user.save(update_fields=["has_employer_role"])

        own_order = ServiceOrder.objects.create(
            employer=emp_profile,
            category=active_category,
            title="O'z buyurtmam",
            description="Test o'z buyurtmasi",
            budget=Decimal("300000.00"),
            location="Toshkent",
            status=OrderStatus.PUBLISHED,
        )
        r = auth_client(user).post(
            "/api/v1/applications/",
            {"order": str(own_order.id), "cover_message": "Self apply", "proposed_price": "300000.00"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_withdrawn_application_cannot_be_accepted(self, auth_client, verified_worker, employer_pair, published_order):
        w_user, _ = verified_worker
        e_user, _ = employer_pair
        w_client = auth_client(w_user)
        e_client = auth_client(e_user)

        app_resp = w_client.post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Ariza matni", "proposed_price": "450000.00"},
            format="json",
        )
        app_id = app_resp.data["data"]["id"]

        w_draw = w_client.post(f"/api/v1/applications/{app_id}/withdraw/")
        assert w_draw.status_code == status.HTTP_200_OK
        assert w_draw.data["data"]["status"] == "WITHDRAWN"

        acc = e_client.post(f"/api/v1/applications/{app_id}/accept/")
        assert acc.status_code == status.HTTP_400_BAD_REQUEST

    def test_direct_invitation_accept_reject_cancel_and_expiry(
        self, auth_client, employer_pair, verified_worker, published_order, active_category
    ):
        e_user, e_profile = employer_pair
        w_user, w_profile = verified_worker
        e_client = auth_client(e_user)
        w_client = auth_client(w_user)

        # Send invitation
        inv_resp = e_client.post(
            "/api/v1/invitations/",
            {
                "order": str(published_order.id),
                "worker": str(w_profile.id),
                "message": "Sizni taklif qilaman",
                "proposed_budget": "500000.00",
            },
            format="json",
        )
        assert inv_resp.status_code == status.HTTP_201_CREATED
        inv_id = inv_resp.data["data"]["id"]

        # Worker accepts
        acc_resp = w_client.post(f"/api/v1/invitations/{inv_id}/accept/")
        assert acc_resp.status_code == status.HTTP_200_OK
        assert acc_resp.data["data"]["status"] == "ACCEPTED"
        published_order.refresh_from_db()
        assert published_order.status == OrderStatus.IN_PROGRESS
        assert published_order.assigned_worker_id == w_profile.id

        # Expired invitation test on second order
        order2 = ServiceOrder.objects.create(
            employer=e_profile,
            category=active_category,
            title="Ikkinchi buyurtma",
            description="Muddati o'tgan taklif testi",
            budget=Decimal("400000.00"),
            location="Toshkent",
            status=OrderStatus.PUBLISHED,
        )
        exp_inv = OrderInvitation.objects.create(
            order=order2,
            employer=e_profile,
            worker=w_profile,
            message="Eski taklif",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        exp_resp = w_client.post(f"/api/v1/invitations/{exp_inv.id}/accept/")
        assert exp_resp.status_code == status.HTTP_400_BAD_REQUEST
        exp_inv.refresh_from_db()
        assert exp_inv.status == InvitationStatus.EXPIRED

    def test_unverified_worker_can_receive_and_accept_invitation(
        self, auth_client, employer_pair, unverified_worker, published_order
    ):
        """Batch 16: An unverified worker can be directly invited and accept the invitation."""
        e_user, e_profile = employer_pair
        u_user, u_profile = unverified_worker
        e_client = auth_client(e_user)
        u_client = auth_client(u_user)

        # Employer invites unverified worker
        inv_resp = e_client.post(
            "/api/v1/invitations/",
            {
                "order": str(published_order.id),
                "worker": str(u_profile.id),
                "message": "Ixtiyoriy KYC taklifi",
                "proposed_budget": "600000.00",
            },
            format="json",
        )
        assert inv_resp.status_code == status.HTTP_201_CREATED
        inv_id = inv_resp.data["data"]["id"]

        # Unverified worker accepts invitation
        acc_resp = u_client.post(f"/api/v1/invitations/{inv_id}/accept/")
        assert acc_resp.status_code == status.HTTP_200_OK
        assert acc_resp.data["data"]["status"] == "ACCEPTED"
        published_order.refresh_from_db()
        assert published_order.status == OrderStatus.IN_PROGRESS
        assert published_order.assigned_worker_id == u_profile.id

    def test_inactive_and_anonymized_workers_cannot_apply_or_accept_invitations(
        self, auth_client, employer_pair, unverified_worker, published_order
    ):
        """Batch 16: Security boundary preserved - inactive or anonymized accounts remain strictly blocked."""
        e_user, e_profile = employer_pair
        u_user, u_profile = unverified_worker

        # Deactivate user
        u_user.is_active = False
        u_user.save(update_fields=["is_active"])

        # Deactivated worker cannot apply
        r_app = auth_client(u_user).post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Nofaol ariza", "proposed_price": "500000.00"},
            format="json",
        )
        assert r_app.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # Restore active, set anonymized
        u_user.is_active = True
        u_user.is_anonymized = True
        u_user.phone_number = None
        u_user.save(update_fields=["is_active", "is_anonymized", "phone_number"])

        r_anon = auth_client(u_user).post(
            "/api/v1/applications/",
            {"order": str(published_order.id), "cover_message": "Anonim ariza", "proposed_price": "500000.00"},
            format="json",
        )
        assert r_anon.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db(transaction=True)
class TestHiringConcurrency:
    def test_concurrent_application_acceptance_and_invitation_acceptance_race(self, active_category):
        emp_user = UserFactory(phone_number="+998905550001", role="EMPLOYER", has_employer_role=True, has_worker_role=False)
        emp = EmployerProfile.objects.create(user=emp_user, full_name="Race Employer", phone_number=emp_user.phone_number)

        w1_user = UserFactory(phone_number="+998905550002", role="WORKER", has_worker_role=True)
        w1 = WorkerProfile.objects.create(
            user=w1_user, full_name="Worker One", phone_number=w1_user.phone_number,
            is_verified=True, verification_status=VerificationStatus.VERIFIED,
        )

        w2_user = UserFactory(phone_number="+998905550003", role="WORKER", has_worker_role=True)
        w2 = WorkerProfile.objects.create(
            user=w2_user, full_name="Worker Two", phone_number=w2_user.phone_number,
            is_verified=True, verification_status=VerificationStatus.VERIFIED,
        )

        order = ServiceOrder.objects.create(
            employer=emp,
            category=active_category,
            title="Concurrency Race Order",
            description="Only one worker may win",
            budget=Decimal("1000000.00"),
            location="Toshkent",
            status=OrderStatus.PUBLISHED,
        )

        app = OrderApplication.objects.create(
            order=order, worker=w1, cover_message="I can do it", proposed_price=Decimal("900000.00")
        )
        inv = OrderInvitation.objects.create(
            order=order, employer=emp, worker=w2, message="Please join", proposed_budget=Decimal("950000.00")
        )

        barrier = threading.Barrier(2)
        successes = []
        failures = []

        def accept_app_worker():
            try:
                barrier.wait(timeout=5)
                res = ApplicationService.accept_application(app.id, emp)
                successes.append(("APP", res.id))
            except Exception as exc:
                failures.append(("APP", type(exc).__name__, str(exc)))
            finally:
                connections.close_all()

        def accept_inv_worker():
            try:
                barrier.wait(timeout=5)
                res = InvitationService.accept_invitation(inv.id, w2)
                successes.append(("INV", res.id))
            except Exception as exc:
                failures.append(("INV", type(exc).__name__, str(exc)))
            finally:
                connections.close_all()

        t1 = threading.Thread(target=accept_app_worker)
        t2 = threading.Thread(target=accept_inv_worker)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert len(successes) == 1, f"Expected exactly 1 winner, got successes={successes}, failures={failures}"
        assert len(failures) == 1

        order.refresh_from_db()
        assert order.status == OrderStatus.IN_PROGRESS
        assert order.assigned_worker_id in (w1.id, w2.id)

        accepted_apps = OrderApplication.objects.filter(order=order, status=ApplicationStatus.ACCEPTED).count()
        accepted_invs = OrderInvitation.objects.filter(order=order, status=InvitationStatus.ACCEPTED).count()
        assert accepted_apps + accepted_invs == 1
