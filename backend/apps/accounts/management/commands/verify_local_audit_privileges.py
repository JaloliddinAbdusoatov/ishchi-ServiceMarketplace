"""Separately approved, rollback-only PostgreSQL runtime-role verification."""
import secrets
import uuid
from unittest.mock import patch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction, DatabaseError
from apps.accounts.models import AccountDeletionAudit, User


TABLES = ("accounts_deletion_audit", "django_admin_log")


def preflight():
    """Refuse unsafe privileges before even attempting a forbidden statement."""
    from apps.common.db_authorization import authorize
    if settings.IS_PRODUCTION or getattr(settings, "LOCAL_TARGET_KIND", "") != "work" or connection.vendor != "postgresql":
        raise CommandError("Exact local working PostgreSQL runtime context required.")
    authorize(connection.get_connection_params(), "audit_privilege_probe")
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user, session_user")
        if cursor.fetchone() != ("ishchi_local_app", "ishchi_local_app"):
            raise CommandError("Runtime login/current role mismatch.")
        cursor.execute("SELECT has_schema_privilege(current_user,'public','CREATE'),has_database_privilege(current_user,current_database(),'CREATE')")
        if cursor.fetchone() != (False, False):
            raise CommandError("Runtime still has schema/database CREATE; rejection probes refused.")
        for table in TABLES:
            cursor.execute("""SELECT pg_get_userbyid(c.relowner),
                has_table_privilege(current_user,c.oid,'SELECT'),has_table_privilege(current_user,c.oid,'INSERT'),
                has_table_privilege(current_user,c.oid,'UPDATE'),has_table_privilege(current_user,c.oid,'DELETE'),
                has_table_privilege(current_user,c.oid,'TRUNCATE'),pg_has_role(current_user,c.relowner,'MEMBER')
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relname=%s""", [table])
            if cursor.fetchone() != ("ishchi_local_owner", True, True, False, False, False, False):
                raise CommandError("Unsafe audit ownership/grants: NO mutation/rejection statements attempted.")


def expect_denied(sql, params=()):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
    except DatabaseError as exc:
        cause = exc.__cause__
        if getattr(cause, "sqlstate", None) == "42501":
            return
        raise CommandError("Expected insufficient_privilege, received another database error.") from None
    raise CommandError("Forbidden statement unexpectedly succeeded; outer transaction will roll back.")


def exercise():
    from django.contrib.admin.models import LogEntry, CHANGE
    from rest_framework.test import APIRequestFactory, force_authenticate
    from apps.dashboard.views import AdminUserSuspendView, AdminUserActivateView
    with transaction.atomic():
        preflight()
        expect_denied('CREATE TABLE public._ishchi_runtime_ddl_probe_' + uuid.uuid4().hex + ' (id integer)')
        expect_denied('SET ROLE ishchi_local_owner')
        admin = User.objects.filter(role="ADMIN", is_staff=True, is_active=True, is_anonymized=False).first()
        if admin is None:
            raise CommandError("An existing active administrator is required; no bootstrap is performed.")
        deletion = AccountDeletionAudit.objects.create(user_id=uuid.uuid4(), performed_by_id=admin.pk,
            phone_hash="0" * 64, role="WORKER", reason="Rollback-only privilege probe")
        # Explicit negative ID avoids advancing the audit sequence for this fixture.
        entry = LogEntry.objects.create(id=-secrets.randbelow(2**30)-1, user=admin, content_type=None,
            object_id=str(uuid.uuid4()), object_repr="Rollback-only probe", action_flag=CHANGE, change_message="probe")
        for table, pk in ((TABLES[0], deletion.pk), (TABLES[1], entry.pk)):
            expect_denied(f'UPDATE public."{table}" SET id=id WHERE id=%s', [pk])
            expect_denied(f'DELETE FROM public."{table}" WHERE id=%s', [pk])
            # Executed only after explicit target/scope approval AND no-TRUNCATE preflight.
            expect_denied(f'TRUNCATE TABLE ONLY public."{table}"')
        phone = "+998" + str(secrets.randbelow(10**9)).zfill(9)
        if User.objects.filter(phone_number=phone).exists():
            raise CommandError("Synthetic identifier collision; no existing account is used.")
        subject = User.objects.create_user(phone_number=phone, full_name="Rollback-only privilege probe")
        factory = APIRequestFactory()

        def action(view):
            request = factory.post("/", {}, format="json")
            force_authenticate(request, user=admin)
            return view.as_view()(request, user_id=subject.pk)

        if action(AdminUserSuspendView).status_code != 200:
            raise CommandError("Normal administrator mutation failed.")
        if not LogEntry.objects.filter(user=admin, object_id=str(subject.pk), change_message="account.suspended").exists():
            raise CommandError("Administrator action did not insert its audit event.")

        def fail_audit(**kwargs):
            # A real PostgreSQL NOT NULL failure, not a simulated Python exception.
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO public.django_admin_log (user_id) VALUES (NULL)")

        with patch("apps.accounts.services.audit_service.LogEntry.objects.create", side_effect=fail_audit):
            response = action(AdminUserActivateView)
        subject.refresh_from_db()
        if response.status_code != 409 or response.data.get("error", {}).get("code") != "integrity_conflict" or subject.is_active or subject.account_status != "SUSPENDED":
            raise CommandError("Audit INSERT failure did not roll back the business mutation.")
        transaction.set_rollback(True)
    # PostgreSQL sequences may advance despite rollback; no test rows persist.


class Command(BaseCommand):
    help = "Default no-query dry run; --exercise requires separate audit_privilege_probe approval after role correction."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--exercise", action="store_true")

    def handle(self, *args, **options):
        if not options["exercise"]:
            self.stdout.write("DRY RUN: no connection, SQL, account or privilege change.")
            return
        exercise()
        self.stdout.write("PASS: both audit INSERTs, six audit SQLSTATE 42501 rejections, runtime DDL/SET ROLE rejection, administrator audit and real INSERT-failure business rollback; all probe rows rolled back.")
