"""Live localhost verification with NEW synthetic accounts and jobs; never resets data.

Only run after explicit owner approval for working-target synthetic writes.
Administrator credentials are entered interactively and retained only in memory.
Plaintext credential files and automatic administrator bootstrap are retired.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import getpass
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify(credentials):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    checks = []

    def request(path, *, method="GET", body=None, token=None, expected=(200,), raw=False):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Only paths on the approved localhost application are permitted")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers, method=method)
        try:
            response = opener.open(req, timeout=15)
        except urllib.error.HTTPError as failure:
            response = failure
        with response:
            if response.status not in expected:
                raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}")
            content = response.read()
            return content if raw else json.loads(content)

    html = request("/", raw=True).decode()
    assert 'id="root"' in html
    asset = re.search(r'(?:src|href)="(/assets/[^\"]+\.js)"', html)
    assert asset
    assert len(request(asset.group(1), raw=True)) > 100
    ready = request("/api/v1/health/ready/")
    assert ready["database"]["status"] == ready["redis"]["status"] == "ok"
    checks.extend(["react_and_assets", "postgres_and_redis_readiness"])
    admin_tokens = request("/api/v1/auth/login/", method="POST", body={
        "phone_number": credentials["phone_number"], "password": credentials["password"]})["data"]["tokens"]
    admin = admin_tokens["access"]
    assert request("/api/v1/admin/dashboard/", token=admin)["success"]
    checks.append("real_admin_password_auth")
    run_id = secrets.token_hex(5)
    category = request("/api/v1/categories/", method="POST", token=admin, expected=(201,), body={
        "slug": "local-verification-" + run_id, "name": "Synthetic local verification " + run_id})["data"]["id"]
    accounts = []
    for role in ("EMPLOYER", "WORKER", "WORKER", "WORKER"):
        payload = {"phone_number": "+99893" + f"{secrets.randbelow(10 ** 7):07d}", "password": secrets.token_urlsafe(30),
                   "role": role, "full_name": "Synthetic local " + role + " " + run_id, "location": "Toshkent"}
        account = request("/api/v1/auth/register/", method="POST", body=payload, expected=(201,))["data"]
        assert not account["user"]["is_phone_verified"]
        login = request("/api/v1/auth/login/", method="POST", body=payload)["data"]
        accounts.append({"user": account["user"], "token": login["tokens"]["access"]})
    employer, first, second, other = accounts
    for worker in (first, second):
        profile = request("/api/v1/profiles/worker/", method="PATCH", token=worker["token"], body={"bio": "Synthetic local verification"})
        assert not profile["data"]["is_verified"]
        request("/api/v1/profiles/worker/categories/", method="PUT", token=worker["token"], body={
            "categories": [{"category_id": category, "is_primary": True}]})
    request("/api/v1/admin/dashboard/", token=first["token"], expected=(403,))
    checks.extend(["phone_password_registration_login", "optional_phone_and_kyc", "profiles_categories_and_roles"])

    def create_job(capacity):
        data = request("/api/v1/orders/", method="POST", token=employer["token"], expected=(201,), body={
            "category": category, "title": "Synthetic local job " + run_id, "description": "Authorized local verification",
            "budget": "200000.00", "location": "Toshkent", "status": "DRAFT", "capacity": capacity})["data"]
        request(f"/api/v1/orders/{data['id']}/publish/", method="POST", token=employer["token"])
        return data["id"]

    job = create_job(2)
    applications = []
    for worker in (first, second, other):
        body = {"order": job, "cover_message": "Synthetic available worker", "proposed_price": "100000.00"}
        app = request("/api/v1/applications/", method="POST", token=worker["token"], body=body, expected=(201,))["data"]
        applications.append(app["id"])
    request("/api/v1/applications/", method="POST", token=first["token"], body={
        "order": job, "cover_message": "Duplicate synthetic request", "proposed_price": "100000.00"}, expected=(409,))
    for app in applications[:2]:
        request(f"/api/v1/applications/{app}/accept/", method="POST", token=employer["token"])
    request(f"/api/v1/applications/{applications[2]}/accept/", method="POST", token=employer["token"], expected=(400, 409))
    request(f"/api/v1/applications/{applications[0]}/accept/", method="POST", token=employer["token"], expected=(400, 409))
    checks.append("publication_multiworker_duplicate_and_capacity")
    request("/api/v1/chat/conversations/", method="POST", token=other["token"], body={"order": job}, expected=(403,))
    conv = request("/api/v1/chat/conversations/", method="POST", token=second["token"], body={"order": job}, expected=(200, 201))["data"]["id"]
    for actor in (employer, second):
        request(f"/api/v1/chat/conversations/{conv}/messages/", method="POST", token=actor["token"],
                body={"content": "Synthetic work update"}, expected=(201,))
    request(f"/api/v1/chat/conversations/{conv}/messages/", token=other["token"], expected=(403,))
    assert request("/api/v1/notifications/", token=second["token"])["count"] > 0
    checks.append("authorized_chat_and_notifications")
    request(f"/api/v1/orders/{job}/complete/", method="POST", token=employer["token"])
    for worker in (first, second):
        body = {"order": job, "rating": 5, "reviewee": worker["user"]["id"]}
        request("/api/v1/reviews/", method="POST", token=employer["token"], body=body, expected=(201,))
        request("/api/v1/reviews/", method="POST", token=employer["token"], body=body, expected=(409,))
    request("/api/v1/reviews/", method="POST", token=second["token"], body={"order": job, "rating": 4}, expected=(201,))
    checks.append("completion_and_review_uniqueness")
    invitation_job = create_job(1)
    other_profile = request("/api/v1/profiles/worker/", token=other["token"])["data"]["id"]
    invitation = request("/api/v1/invitations/", method="POST", token=employer["token"], expected=(201,), body={
        "order": invitation_job, "worker": other_profile})["data"]["id"]
    request(f"/api/v1/invitations/{invitation}/accept/", method="POST", token=other["token"])
    request(f"/api/v1/orders/{invitation_job}/complete/", method="POST", token=employer["token"])
    checks.append("invitation_hiring")
    assert request("/api/v1/payments/status/")["data"]["enabled"] is False
    request("/api/v1/payments/status/", method="POST", body={"amount": 1}, expected=(405,))
    checks.append("payments_disabled")
    request("/api/v1/auth/logout-all/", method="POST", token=first["token"], body={})
    request("/api/v1/auth/me/", token=first["token"], expected=(401,))
    checks.append("real_session_revocation")
    return {"verified_at": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
            "checks": checks, "synthetic_jobs": [job, invitation_job], "working_data_flushed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", help=argparse.SUPPRESS)
    parser.add_argument("--bootstrap-admin", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-synthetic-writes", action="store_true", help="Requires separate approval for new synthetic accounts/jobs.")
    parser.add_argument("--report", type=Path, default=ROOT / "deploy/.local/live-verification.json")
    args = parser.parse_args(argv)
    if args.credentials or args.bootstrap_admin:
        parser.error("Plaintext credential files and administrator bootstrap are retired. Rotate the exposed credential, then use interactive login.")
    if not args.allow_synthetic_writes:
        parser.error("This verifier creates synthetic data. Independent owner approval and --allow-synthetic-writes are required.")
    if not sys.stdin.isatty():
        parser.error("Interactive login is required; never pipe or store administrator passwords.")
    credentials = {"phone_number": input("Administrator phone number: ").strip(), "password": getpass.getpass("Administrator password (hidden): ")}
    try:
        report = verify(credentials)
    finally:
        credentials.clear()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS: " + ", ".join(report["checks"]))
    print("Working synthetic records retained; no reset, flush or real-user deletion")


if __name__ == "__main__":
    main()
