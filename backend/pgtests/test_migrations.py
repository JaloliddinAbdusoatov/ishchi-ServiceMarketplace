"""Authorized disposable PostgreSQL only: migration reversal and commit checks."""
import pytest
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.applications.models import OrderApplication
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

pytestmark = pytest.mark.django_db(transaction=True)


def test_hiring_migration_reverse_reapply_and_second_migrate_is_noop():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("orders", "0003_payment_display_label")])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regprocedure('public.ishchi_check_hiring(uuid)'), to_regprocedure('public.ishchi_hiring_integrity_event()')")
            assert cursor.fetchone() == (None, None)
            cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname='ishchi_hiring_integrity'")
            assert cursor.fetchone()[0] == 0
    finally:
        MigrationExecutor(connection).migrate(latest)
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname='ishchi_hiring_integrity' AND tgdeferrable AND tginitdeferred")
        assert cursor.fetchone()[0] == 4
    call_command("migrate", interactive=False, verbosity=0)
    executor = MigrationExecutor(connection)
    assert executor.migration_plan(executor.loader.graph.leaf_nodes()) == []
    # Sprint 4 added a separate outbox migration; cover its reversal too.
    try:
        executor.migrate([("common", None)])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.common_mediadeletiontask')")
            assert cursor.fetchone()[0] is None
    finally:
        MigrationExecutor(connection).migrate(latest)
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "common_mediadeletiontask")
        assert constraints["uq_pending_media_erasure"]["unique"]


def test_deferred_failure_at_commit_rolls_back_request_and_notification(employer_pair, unverified_worker, published_order):
    _, worker = unverified_worker
    owner, _ = employer_pair
    count = Notification.objects.count()
    # No SET CONSTRAINTS: failure must emerge when the outer transaction commits.
    with pytest.raises(IntegrityError) as failure:
        with transaction.atomic():
            app = OrderApplication.objects.create(order=published_order, worker=worker, proposed_price=100, status="ACCEPTED")
            NotificationService.notify(recipient=owner, event_type="NEW_APPLICATION", title="Synthetic rollback", message="Synthetic")
    assert failure.value.__cause__.sqlstate == "23514"
    assert not OrderApplication.objects.filter(pk=app.pk).exists()
    assert Notification.objects.count() == count
    assert published_order.assigned_workers.count() == 0


def test_deferred_checks_allow_valid_orm_write_sequence(employer_pair, unverified_worker, published_order):
    from apps.applications.services import ApplicationService
    _, employer = employer_pair
    _, worker = unverified_worker
    app = ApplicationService.submit_application(worker, published_order.pk, "Synthetic", 100)
    # The service marks ACCEPTED before writing membership; immediate checks would break it.
    with transaction.atomic():
        ApplicationService.accept_application(app.pk, employer)
    app.refresh_from_db()
    assert app.status == "ACCEPTED"
    assert published_order.assigned_workers.filter(pk=worker.pk).exists()
