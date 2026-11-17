"""Local-only Docker smoke/syntax validation with synthetic fixtures and no network.

Build images first. Never starts Compose, PostgreSQL, Redis or a public listener.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default="default")
    parser.add_argument("--backend-image", default="ishchi-backend:sprint4")
    parser.add_argument("--frontend-image", default="ishchi-frontend:sprint4")
    args = parser.parse_args()
    docker = ["docker", "--context", args.context]

    def run(command, *, expected=0):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        if (result.returncode == 0) != (expected == 0):
            raise RuntimeError("Local container validation failed: " + result.stderr[-2000:])
        return result.stdout

    endpoint = json.loads(run(docker + ["context", "inspect", "--format", "{{json .Endpoints.docker.Host}}", args.context]))
    if not endpoint.startswith(("unix://", "npipe://")):
        raise SystemExit("Refusing a remote Docker context")
    run(docker + ["compose", "--env-file", "deploy/.env.example", "-f", "deploy/compose.production.yml",
        "config", "--no-env-resolution", "--quiet"])
    print("PASS: Compose configuration (no secret env file loaded)")
    base = docker + ["run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,mode=1777"]
    for image, uid in ((args.backend_image, "10001:10001"), (args.frontend_image, "101:101")):
        user = run(docker + ["image", "inspect", "--format", "{{json .Config.User}}", image]).strip()
        assert json.loads(user) == uid
    print("PASS: both runtime images select non-root users")
    run(base + ["--entrypoint", "python", args.backend_image, "-c",
        "from pathlib import Path; p=Path('/app'); assert not any((p/n).exists() for n in ('.env','.local','tests','local_tools','.venv')); assert not list(p.rglob('*.sqlite3'))"])
    run(base + ["--entrypoint", "sh", args.frontend_image, "-c",
        "test ! -e /app/node_modules && test ! -e /usr/share/nginx/html/.env && test -f /usr/share/nginx/html/index.html"])
    print("PASS: runtime images omit local data, environments and build dependency trees")
    run(base + ["--entrypoint", "python", args.backend_image, "manage.py", "check"], expected=1)
    print("PASS: production startup refuses missing configuration")
    with tempfile.TemporaryDirectory(prefix="ishchi-container-check-") as directory:
        temp = Path(directory).resolve()
        assert temp.parent == Path(tempfile.gettempdir()).resolve() and temp.name.startswith("ishchi-container-check-")
        temp.chmod(0o755)
        uid = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "10001:10001"
        # Keys are disposable test fixtures only, never production identities.
        run(docker + ["run", "--rm", "--network", "none", "--user", uid,
            "--mount", f"type=bind,src={temp},dst=/fixtures", "--entrypoint", "openssl", args.backend_image,
            "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=example.uz",
            "-keyout", "/fixtures/tls.key", "-out", "/fixtures/tls.crt"])
        # Docker Desktop bind metadata may not reflect host os.chmod. These are
        # disposable fixtures; production key ACLs must be set by the operator.
        run(docker + ["run", "--rm", "--network", "none", "--user", uid,
            "--mount", f"type=bind,src={temp},dst=/fixtures", "--entrypoint", "chmod", args.backend_image,
            "0644", "/fixtures/tls.key", "/fixtures/tls.crt"])
        for path in temp.iterdir():
            path.chmod(0o644)  # Synthetic fixtures must be readable by nginx UID 101.
        mount = lambda source, destination: ["--mount", f"type=bind,src={source},dst={destination},readonly"]
        run(base + mount(ROOT / "deploy/nginx.conf.example", "/etc/nginx/nginx.conf")
            + mount(temp / "tls.crt", "/run/secrets/tls_certificate")
            + mount(temp / "tls.key", "/run/secrets/tls_key")
            + ["--entrypoint", "nginx", args.frontend_image, "-t"])
        print("PASS: nginx -t with temporary synthetic certificate (real TLS NOT VERIFIED)")
        config = {
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64), "DJANGO_ALLOWED_HOSTS": "example.uz",
            "CSRF_TRUSTED_ORIGINS": "https://example.uz", "CORS_ALLOWED_ORIGINS": "https://example.uz",
            "TRUST_HTTPS_PROXY": "true", "TRUSTED_PROXY_IPS": "127.0.0.1", "HEALTHCHECK_HOST": "example.uz",
            "DB_NAME": "ishchi_marketplace", "DB_HOST": "db.invalid", "DB_USER": "runtime", "DB_PASSWORD": "synthetic-only",
            "DB_SSLROOTCERT": "/fixtures/tls.crt", "REDIS_URL": "rediss://runtime:synthetic-only@cache.invalid:6379/1",
            "REDIS_SSLROOTCERT": "/fixtures/tls.crt", "SMS_BACKEND": "disabled",
        }
        env = temp / "synthetic.env"
        env.write_text("".join(f"{key}={value}\n" for key, value in config.items()), encoding="utf-8")
        smoke = r'''set -eu
gunicorn --config config/gunicorn.py config.wsgi:application &
app_pid=$!
trap 'kill -TERM "$app_pid" 2>/dev/null || true; wait "$app_pid" || true' EXIT
python - <<'PY'
import time, urllib.request, urllib.error
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(40):
    try:
        req=urllib.request.Request('http://127.0.0.1:8000/api/v1/health/live/',headers={'Host':'example.uz'})
        with opener.open(req, timeout=1) as response:
            assert response.status == 200
        break
    except OSError:
        time.sleep(.1)
else:
    raise AssertionError('Liveness did not become available')
req=urllib.request.Request('http://127.0.0.1:8000/api/v1/health/ready/',headers={'Host':'example.uz','X-Forwarded-Proto':'https'})
try:
    opener.open(req,timeout=3)
except urllib.error.HTTPError as exc:
    assert exc.code == 503
else:
    raise AssertionError('Unauthorized dependencies must not become ready')
print('PASS: Gunicorn loopback liveness 200; dependency readiness 503; no service network')
PY
python -m config.container_health
kill -TERM "$app_pid"
wait "$app_pid"
trap - EXIT
'''
        print(run(base + ["--env-file", str(env)] + mount(temp / "tls.crt", "/fixtures/tls.crt")
            + ["--entrypoint", "sh", args.backend_image, "-c", smoke]).strip())
    print("PASS: disposable fixtures removed; no deployment or infrastructure services started")


if __name__ == "__main__":
    main()
