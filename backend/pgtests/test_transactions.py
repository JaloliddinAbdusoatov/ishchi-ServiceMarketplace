"""Independent real PostgreSQL connections; failures/deadlocks are test failures."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch
from datetime import timedelta
import time

import pytest
from django.db import DatabaseError, IntegrityError, connection, connections, transaction
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AccountDeletionAudit, User
from apps.accounts.services.auth_service import AuthService
from apps.applications.models import OrderApplication
from apps.applications.services import ApplicationService
from apps.invitations.services import InvitationService
from apps.common.exceptions import BusinessRuleViolation
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.profiles.models import WorkerProfile
from apps.orders.services import OrderService
from apps.common.models import MediaDeletionTask
from apps.common.media_erasure import process_media_erasure
from tests.conftest import UserFactory

pytestmark = pytest.mark.django_db(transaction=True)


def submit(worker, order):
    return ApplicationService.submit_application(worker, order.pk, "Synthetic application", 100)


@pytest.mark.parametrize("capacity", [1, 2])
@pytest.mark.parametrize("mixed", [False, True])
def test_concurrent_hiring_capacity_and_duplicate(employer_pair, unverified_worker, published_order, capacity, mixed):
    _, employer = employer_pair
    _, first = unverified_worker
    published_order.capacity = capacity
    published_order.save(update_fields=["capacity"])
    second_user = UserFactory()
    second = WorkerProfile.objects.create(user=second_user, full_name="Second worker", phone_number=second_user.phone_number)
    apps = [submit(worker, published_order) for worker in (first, second)]
    invitation = InvitationService.send_invitation(employer, published_order.pk, first.pk) if mixed else None
    barrier = Barrier(3)

    def hire(index):
        connections.close_all()
        try:
            barrier.wait(timeout=10)
            if mixed and index == 1:
                InvitationService.accept_invitation(invitation.pk, first)
            else:
                ApplicationService.accept_application(apps[0 if index < 2 else 1].pk, employer)
            return "hired"
        except BusinessRuleViolation as exc:
            assert exc.get_codes() in {"order_already_assigned", "worker_already_assigned", "invalid_application_transition", "invalid_invitation_transition"}
            return "rejected"
        except DatabaseError as exc:
            raise AssertionError(f"Concurrent hiring failed: SQLSTATE={getattr(exc.__cause__, 'sqlstate', None)}; user -> order -> worker -> request locks") from exc
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(hire, index) for index in range(3)]
        results = [future.result(timeout=25) for future in futures]
    assert results.count("hired") == capacity
    assert results.count("rejected") == 3 - capacity
    published_order.refresh_from_db()
    assert published_order.hired_worker_count == capacity
    assert OrderApplication.objects.filter(order=published_order, status="ACCEPTED").count() == capacity


@pytest.mark.parametrize("mutation", ["deactivate", "anonymize", "unavailable", "employer_suspend", "cancel_order"])
def test_account_mutation_committing_while_hiring_waits(employer_pair, unverified_worker, published_order, mutation):
    owner, employer = employer_pair
    user, worker = unverified_worker
    application = submit(worker, published_order)
    started = Event()
    backend_pid = []

    def hire():
        connections.close_all()
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                backend_pid.append(cursor.fetchone()[0])
            started.set()
            ApplicationService.accept_application(application.pk, employer)
            return "hired"
        except BusinessRuleViolation as exc:
            expected = {"unavailable": "worker_unavailable", "cancel_order": "invalid_application_transition"}.get(mutation, "account_not_active")
            assert exc.get_codes() == expected
            return "rejected"
        except DatabaseError as exc:
            raise AssertionError(f"{mutation} racing hire: SQLSTATE={getattr(exc.__cause__, 'sqlstate', None)}; account/order/profile lock path") from exc
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            if mutation == "unavailable":
                WorkerProfile.objects.select_for_update().get(pk=worker.pk)
            elif mutation == "cancel_order":
                OrderService.cancel_order(published_order.pk, employer)
            else:
                User.objects.select_for_update().get(pk=owner.pk if mutation == "employer_suspend" else user.pk)
            if mutation == "deactivate":
                User.objects.filter(pk=user.pk).update(is_active=False, account_status="SUSPENDED")
            elif mutation == "anonymize":
                AuthService.anonymize_and_delete_account(user, password="StrongPass2026!")
            elif mutation == "employer_suspend":
                User.objects.filter(pk=owner.pk).update(account_status="SUSPENDED")
            elif mutation == "unavailable":
                WorkerProfile.objects.filter(pk=worker.pk).update(is_available=False)
            future = pool.submit(hire)
            assert started.wait(5)
            deadline = time.monotonic() + 5
            blocked = False
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", [backend_pid[0]])
                    blocked = cursor.fetchone()[0]
                if blocked:
                    break
                time.sleep(0.02)
            assert blocked, "Hiring never reached a real PostgreSQL row-lock wait"
        assert future.result(timeout=20) == "rejected"
    published_order.refresh_from_db()
    assert published_order.hired_worker_count == 0
    if mutation == "anonymize":
        assert User.objects.get(pk=user.pk).is_anonymized
        assert AccountDeletionAudit.objects.filter(user_id=user.pk).count() == 1
    elif mutation == "cancel_order":
        assert published_order.status == "CANCELLED"


def test_hire_commits_before_waiting_cancellation(employer_pair, unverified_worker, published_order):
    _, employer = employer_pair
    _, worker = unverified_worker
    app = submit(worker, published_order)
    started = Event()
    backend_pid = []

    def cancel():
        connections.close_all()
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                backend_pid.append(cursor.fetchone()[0])
            started.set()
            OrderService.cancel_order(published_order.pk, employer)
        except DatabaseError as exc:
            raise AssertionError(f"Hire racing cancellation: SQLSTATE={getattr(exc.__cause__, 'sqlstate', None)}; cancellation order -> requests") from exc
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            ApplicationService.accept_application(app.pk, employer)
            future = pool.submit(cancel)
            assert started.wait(5)
            deadline = time.monotonic() + 5
            blocked = False
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", [backend_pid[0]])
                    blocked = cursor.fetchone()[0]
                if blocked:
                    break
                time.sleep(0.02)
            assert blocked, "Cancellation never waited for the hiring transaction"
        future.result(timeout=20)
    published_order.refresh_from_db()
    app.refresh_from_db()
    assert published_order.status == "CANCELLED"
    # Cancellation retains historical hires; there is no individual unhire API.
    assert published_order.hired_worker_count == 1 and app.status == "ACCEPTED"


def test_induced_failure_rolls_back_entire_hire(employer_pair, unverified_worker, published_order):
    _, employer = employer_pair
    _, worker = unverified_worker
    application = submit(worker, published_order)
    count = Notification.objects.count()
    original = NotificationService.notify

    def fail_after_notification(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("Induced failure after database writes")

    with patch.object(NotificationService, "notify", side_effect=fail_after_notification):
        with pytest.raises(RuntimeError, match="Induced failure"):
            ApplicationService.accept_application(application.pk, employer)
    application.refresh_from_db()
    published_order.refresh_from_db()
    assert application.status == "PENDING"
    assert published_order.hired_worker_count == 0 and published_order.status == "PUBLISHED"
    assert Notification.objects.count() == count


@pytest.mark.parametrize("violation", ["accepted_without_hire", "accepted_invitation_without_hire", "team_without_request", "capacity_shrink", "owner_mismatch"])
def test_database_rejects_direct_integrity_bypass(employer_pair, unverified_worker, published_order, violation):
    from apps.invitations.models import OrderInvitation
    from apps.profiles.models import EmployerProfile
    _, employer = employer_pair
    _, worker = unverified_worker
    app = submit(worker, published_order)
    if violation == "capacity_shrink":
        published_order.capacity = 2
        published_order.save(update_fields=["capacity"])
        ApplicationService.accept_application(app.pk, employer)
        other_user = UserFactory()
        other = WorkerProfile.objects.create(user=other_user, full_name="Other worker")
        other_app = submit(other, published_order)
        ApplicationService.accept_application(other_app.pk, employer)
    with pytest.raises(IntegrityError), transaction.atomic():
        if violation == "accepted_without_hire":
            OrderApplication.objects.filter(pk=app.pk).update(status="ACCEPTED")
        elif violation == "accepted_invitation_without_hire":
            OrderInvitation.objects.create(order=published_order, worker=worker, employer=employer, status="ACCEPTED")
        elif violation == "team_without_request":
            published_order.assigned_workers.add(worker)
        elif violation == "capacity_shrink":
            type(published_order).objects.filter(pk=published_order.pk).update(capacity=1)
        else:
            other_user = UserFactory(has_employer_role=True)
            other_owner = EmployerProfile.objects.create(user=other_user, full_name="Other owner")
            OrderInvitation.objects.create(order=published_order, worker=worker, employer=other_owner)
        # Force deferred checks before leaving this transaction/savepoint.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_anonymization_audit_failure_rolls_back_outbox_and_tokens(unverified_worker, tmp_path):
    from apps.accounts.services.auth_service import generate_jwt_pair
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
    user, worker = unverified_worker
    tokens = generate_jwt_pair(user)
    worker.photo.name = "workers/photos/synthetic-rollback.png"
    worker.save(update_fields=["photo"])
    original_name = worker.full_name
    with override_settings(MEDIA_ROOT=tmp_path), patch("apps.common.media_erasure.default_storage.delete") as delete:
        with patch("apps.accounts.services.auth_service.AccountDeletionAudit.objects.create", side_effect=RuntimeError("Induced audit failure")):
            with pytest.raises(RuntimeError, match="Induced audit failure"):
                AuthService.anonymize_and_delete_account(user, require_password=False)
        delete.assert_not_called()
    user.refresh_from_db()
    worker.refresh_from_db()
    assert not user.is_anonymized and user.is_active and worker.full_name == original_name
    assert worker.photo.name == "workers/photos/synthetic-rollback.png"
    assert not MediaDeletionTask.objects.exists() and not AccountDeletionAudit.objects.exists()
    assert not BlacklistedToken.objects.exists()
    from apps.accounts.authentication import MarketplaceJWTAuthentication
    assert MarketplaceJWTAuthentication().get_validated_token(tokens["access"])


def test_committed_outbox_survives_failure_and_retries_real_sandbox_media(unverified_worker, tmp_path):
    user, worker = unverified_worker
    name = "workers/photos/synthetic-commit.png"
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(b"Synthetic erasure fixture")
    worker.photo.name = name
    worker.save(update_fields=["photo"])
    with override_settings(MEDIA_ROOT=tmp_path):
        with patch("apps.common.media_erasure.default_storage.delete", side_effect=OSError("Induced storage failure")):
            AuthService.anonymize_and_delete_account(user, require_password=False)
        task = MediaDeletionTask.objects.get()
        user.refresh_from_db()
        assert user.is_anonymized and AccountDeletionAudit.objects.filter(user_id=user.pk).count() == 1
        assert task.completed_at is None and task.attempts == 1 and task.error_code == "OSError" and path.exists()
        task.next_attempt_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=["next_attempt_at"])
        assert process_media_erasure() == {"completed": 1, "failed": 0}
        task.refresh_from_db()
        assert task.completed_at and task.name == "" and task.attempts == 2 and not path.exists()
