"""Approved working-runtime role check using transient, rollback-only API fixtures."""
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


def exercise():
    from apps.common.db_authorization import authorize
    from apps.accounts.models import User
    from apps.accounts.services.auth_service import generate_jwt_pair
    from rest_framework.test import APIClient
    if settings.IS_PRODUCTION or getattr(settings, "LOCAL_TARGET_KIND", "") != "work" or connection.vendor != "postgresql":
        raise CommandError("Working local PostgreSQL runtime context required.")
    authorize(connection.get_connection_params(), "marketplace_privilege_probe")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user,session_user")
            if cursor.fetchone() != ("ishchi_local_app", "ishchi_local_app"):
                raise CommandError("Runtime role required.")
        admin = User.objects.filter(role="ADMIN", is_staff=True, is_active=True).first()
        if admin is None:
            raise CommandError("Existing administrator required; no bootstrap.")
        client = APIClient(HTTP_HOST="localhost")

        def request(path, *, method="get", data=None, token=None, expected=(200,)):
            client.credentials(**({"HTTP_AUTHORIZATION": "Bearer " + token} if token else {}))
            response = getattr(client, method)("/api/v1/" + path, data or {}, format="json")
            if response.status_code not in expected:
                raise CommandError(f"Runtime API check failed: {method.upper()} {path}, HTTP {response.status_code}.")
            return response.data

        admin_token = generate_jwt_pair(admin)["access"]
        request("admin/dashboard/", token=admin_token)
        suffix = secrets.token_hex(5)
        category = request("categories/", method="post", token=admin_token, expected=(201,),
            data={"slug":"role-probe-"+suffix,"name":"Rollback-only role probe " + suffix})["data"]["id"]
        actors = []
        for role in ("EMPLOYER", "WORKER"):
            phone = "+99893" + str(secrets.randbelow(10**7)).zfill(7)
            if User.objects.filter(phone_number=phone).exists():
                raise CommandError("Synthetic phone collision; no existing user used.")
            body = {"phone_number":phone,"password":secrets.token_urlsafe(30),"role":role,
                "full_name":"Rollback-only " + role,"location":"Toshkent"}
            registered = request("auth/register/", method="post", data=body, expected=(201,))["data"]
            if registered["user"]["is_phone_verified"]:
                raise CommandError("Registration unexpectedly requires or grants phone verification.")
            logged_in = request("auth/login/", method="post", data=body)["data"]
            actors.append((registered["user"], logged_in["tokens"]["access"]))
        employer, worker = actors
        profile = request("profiles/worker/", method="patch", token=worker[1], data={"bio":"Rollback-only probe"})["data"]
        if profile["is_verified"]:
            raise CommandError("Worker fixture unexpectedly KYC-verified.")
        request("profiles/worker/categories/", method="put", token=worker[1], data={"categories":[{"category_id":category,"is_primary":True}]})
        request("admin/dashboard/", token=worker[1], expected=(403,))
        job = request("orders/", method="post", token=employer[1], expected=(201,), data={
            "category":category,"title":"Rollback-only job " + suffix,"description":"Authorized runtime privilege verification",
            "budget":"200000.00","location":"Toshkent","status":"DRAFT","capacity":1})["data"]["id"]
        request(f"orders/{job}/publish/", method="post", token=employer[1])
        application = request("applications/", method="post", token=worker[1], expected=(201,), data={
            "order":job,"cover_message":"Rollback-only application","proposed_price":"100000.00"})["data"]["id"]
        request(f"applications/{application}/accept/", method="post", token=employer[1])
        conversation = request("chat/conversations/", method="post", token=worker[1], expected=(200,201), data={"order":job})["data"]["id"]
        request(f"chat/conversations/{conversation}/messages/", method="post", token=worker[1], expected=(201,), data={"content":"Rollback-only update"})
        if request("notifications/", token=worker[1])["count"] < 1:
            raise CommandError("Hiring did not produce worker notifications.")
        request(f"orders/{job}/complete/", method="post", token=employer[1])
        request("reviews/", method="post", token=employer[1], expected=(201,), data={"order":job,"rating":5,"reviewee":worker[0]["id"]})
        if request("payments/status/")["data"]["enabled"]:
            raise CommandError("Payments must remain disabled.")
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        transaction.set_rollback(True)


class Command(BaseCommand):
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--exercise", action="store_true")

    def handle(self, *args, **options):
        if not options["exercise"]:
            self.stdout.write("DRY RUN: no connection or synthetic writes.")
            return
        exercise()
        self.stdout.write("PASS: runtime registration/password login, optional KYC, admin authorization/audit, publication, application/hiring, chat/notifications, completion/review, deferred constraints, disabled payments; all DB fixtures rolled back.")
