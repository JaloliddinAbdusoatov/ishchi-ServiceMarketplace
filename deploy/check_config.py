"""Offline release invariants; no infrastructure clients or credentials needed."""
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    compose = yaml.safe_load((root / "deploy/compose.production.yml").read_text())
    assert set(compose["services"]) == {"backend", "gateway"}, "Infrastructure services must remain externally provisioned"
    backend, gateway = (compose["services"][name] for name in ("backend", "gateway"))
    for service in (backend, gateway):
        assert service["read_only"] is True and str(service["user"]).split(":")[0] not in ("0", "root")
        assert service["cap_drop"] == ["ALL"] and "no-new-privileges:true" in service["security_opt"]
        assert service["logging"]["options"] == {"max-size": "10m", "max-file": "3"}
        assert service["mem_limit"] and service["pids_limit"] and service["stop_grace_period"]
    assert gateway["network_mode"] == "service:backend"
    assert backend["ports"] == ["127.0.0.1:8080:8080", "127.0.0.1:8443:8443"]
    assert "ports" not in gateway
    env = backend["environment"]
    assert env["DJANGO_SETTINGS_MODULE"] == "config.settings.production" and env["ISHCHI_ENV"] == "production"
    assert env["TRUSTED_PROXY_IPS"] == "127.0.0.1"
    assert env["DJANGO_MEDIA_ROOT"] == "/app/media" and "/app/media" in backend["volumes"][0]
    for directory in ("backend", "frontend"):
        dockerfile = (root / directory / "Dockerfile").read_text()
        images = re.findall(r"^FROM (\S+)", dockerfile, re.M)
        assert images and all(re.search(r"@sha256:[a-f0-9]{64}$", image) for image in images)
        assert "USER " in dockerfile and "HEALTHCHECK " in dockerfile and "STOPSIGNAL " in dockerfile
        assert not re.search(r"\b(manage.py migrate|seed_demo|seed_marketplace|createsuperuser)\b", dockerfile)
        ignore = (root / directory / ".dockerignore").read_text()
        assert "**" in ignore.splitlines() and "**/.env*" in ignore
    nginx = (root / "deploy/nginx.conf.example").read_text()
    for prefix in ("chat", "orders"):
        assert f"location ^~ /media/{prefix}/ {{ return 404; }}" in nginx
    for required in ('proxy_set_header X-Forwarded-For "";', "proxy_set_header X-Real-IP $remote_addr;",
            "proxy_set_header X-Request-ID $request_id;", "client_max_body_size 6m;",
            "location /media/ { return 404; }", "ssl_protocols TLSv1.2 TLSv1.3;", "limit_req_status 429;",
            "proxy_connect_timeout 3s;", "proxy_read_timeout 60s;", "X-Content-Type-Options nosniff always;"):
        assert required in nginx, required
    assert "$request_uri" not in nginx.split("log_format safe", 1)[1].split(";", 1)[0]
    assert "$request " not in nginx and "proxy_set_header Upgrade" not in nginx
    assert 'bind = "127.0.0.1:8000"' in (root / "backend/config/gunicorn.py").read_text()
    redis = (root / "deploy/redis/redis.conf.example").read_text()
    for setting in ("port 0", "protected-mode yes", "appendonly yes", "appendfsync always", "maxmemory-policy noeviction"):
        assert setting in redis
    acl = (root / "deploy/redis/users.acl.example").read_text()
    assert "user default off" in acl and "user ishchi_runtime off resetpass" in acl and "~ishchi:production:*" in acl
    assert "+@all" not in acl and "+flushall" not in acl and "+flushdb" not in acl
    print("PASS: container, proxy, media, logging, namespace and offline-operation invariants")


if __name__ == "__main__":
    check()
