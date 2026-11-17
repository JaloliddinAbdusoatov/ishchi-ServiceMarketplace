"""Actual loopback HTTP smoke test with an ephemeral in-memory SQLite application.

Uses testing settings and synthetic accounts only. No production settings, files,
PostgreSQL/Redis or external sockets are used. Never an application startup command.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def stop_child(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Windows venv python.exe can be a redirector with a separate interpreter
        # child. Terminating only the redirector leaves the server/log handle alive.
        result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"),
            "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=10)
        if result.returncode and process.poll() is None:
            raise RuntimeError("Could not stop the owned smoke process tree")
        process.wait(timeout=5)
    else:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def child(ready_file):
    sys.path.insert(0, str(ROOT / "backend"))
    os.environ.update(DJANGO_SETTINGS_MODULE="config.settings.testing", ISHCHI_ENV="development",
        DJANGO_SECRET_KEY=secrets.token_urlsafe(64), SMS_BACKEND="disabled")
    original_connect = socket.socket.connect

    def loopback_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
            raise AssertionError("Smoke test attempted an external connection")
        return original_connect(sock, address)

    socket.socket.connect = loopback_only
    import django
    django.setup()
    from django.conf import settings
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert settings.DATABASES["default"]["NAME"] == ":memory:"
    assert settings.CACHES["default"]["BACKEND"].endswith("LocMemCache")
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)
    from apps.accounts.models import User
    User.objects.create_superuser(phone_number="+998935588901", password=os.environ["SMOKE_ADMIN_PASSWORD"], full_name="Synthetic smoke operator")
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server
    with make_server("127.0.0.1", 0, get_wsgi_application()) as server:
        Path(ready_file).write_text(str(server.server_port), encoding="ascii")
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child-ready-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child_ready_file:
        child(args.child_ready_file)
        return
    with tempfile.TemporaryDirectory(prefix="ishchi-http-smoke-") as directory:
        temp = Path(directory).resolve()
        assert temp.parent == Path(tempfile.gettempdir()).resolve() and temp.name.startswith("ishchi-http-smoke-")
        ready = temp / "ready"
        password = secrets.token_urlsafe(24)
        env = {**os.environ, "SMOKE_ADMIN_PASSWORD": password}
        with (temp / "child.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, __file__, "--child-ready-file", str(ready)],
                cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                deadline = time.monotonic() + 20
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.1)
                if not ready.exists():
                    raise RuntimeError("Synthetic loopback application did not start")
                base = "http://127.0.0.1:" + ready.read_text(encoding="ascii")
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

                def request(path, *, method="GET", body=None, token=None, expected=200):
                    headers = {"Content-Type": "application/json"}
                    if token:
                        headers["Authorization"] = "Bearer " + token
                    data = json.dumps(body).encode() if body is not None else None
                    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
                    try:
                        response = opener.open(req, timeout=5)
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        assert response.status == expected, f"Unexpected HTTP status for {path}"
                        raw = response.read()
                        return json.loads(raw) if response.headers.get("Content-Type", "").startswith("application/json") else None

                request("/api/v1/health/live/")
                request("/api/v1/health/ready/")
                worker = request("/api/v1/auth/register/", method="POST", expected=201, body={
                    "phone_number": "+998935588902", "password": password, "full_name": "Synthetic worker", "role": "WORKER"})["data"]
                assert worker["user"]["is_phone_verified"] is False
                tokens = worker["tokens"]
                request("/api/v1/auth/login/", method="POST", body={"phone_number": "+998935588902", "password": password})
                request("/api/v1/profiles/worker/", token=tokens["access"])
                request("/api/v1/admin/users/", token=tokens["access"], expected=403)
                admin = request("/api/v1/auth/login/", method="POST", body={"phone_number": "+998935588901", "password": password})["data"]["tokens"]
                request("/api/v1/admin/users/", token=admin["access"])
                request("/api/v1/orders/")
                request("/api/v1/categories/")
                request("/media/chat/attachments/private.txt", expected=404)
                request("/media/orders/images/private.png", expected=404)
                request("/api/v1/chat/messages/00000000-0000-4000-8000-000000000001/attachment/", expected=401)
                assert request("/api/v1/payments/status/")["data"]["enabled"] is False
                request("/api/v1/payments/status/", method="POST", body={}, expected=405)
                request("/api/v1/auth/logout-all/", method="POST", body={}, token=tokens["access"])
                request("/api/v1/auth/me/", token=tokens["access"], expected=401)
                print("PASS: real loopback startup/health, registration/login, admin boundary, marketplace, private media, payments and revocation")
            finally:
                stop_child(process)
    print("PASS: synthetic SQLite app stopped; temporary fixtures removed")


if __name__ == "__main__":
    main()
