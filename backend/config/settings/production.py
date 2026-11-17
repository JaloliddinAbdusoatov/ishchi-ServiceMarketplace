"""Fail-closed production template. PostgreSQL schema deployment remains blocked."""
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403
IS_PRODUCTION = True
DEBUG = False
LOCAL_DEVELOPMENT = False

def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Production requires {name}.")
    return value

SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or any(word in SECRET_KEY.lower() for word in ("insecure", "change-me", "replace", "demo")):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a new random secret of at least 50 characters.")
ALLOWED_HOSTS = [h.strip() for h in required("DJANGO_ALLOWED_HOSTS").split(",")]
if any(not h or "*" in h or h.startswith(".") or "://" in h for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list explicit hostnames.")

def https_origins(name):
    origins = [v.strip() for v in required(name).split(",")]
    for origin in origins:
        parts = urlsplit(origin)
        if parts.scheme != "https" or not parts.hostname or "*" in origin or parts.username or parts.password or parts.path or parts.query or parts.fragment:
            raise ImproperlyConfigured(f"{name} must list explicit HTTPS origins without paths.")
    return origins

CSRF_TRUSTED_ORIGINS = https_origins("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = https_origins("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = False
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Opt in only behind a trusted proxy that strips incoming forwarding headers.
if os.environ.get("TRUST_HTTPS_PROXY") == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    import ipaddress
    TRUSTED_PROXY_IPS = [v.strip() for v in required("TRUSTED_PROXY_IPS").split(",")]
    try:
        for proxy_ip in TRUSTED_PROXY_IPS:
            ipaddress.ip_address(proxy_ip)
    except ValueError:
        raise ImproperlyConfigured("TRUSTED_PROXY_IPS must contain explicit proxy IP addresses.") from None
from .database import postgres_database
DATABASES = {"default": postgres_database(os.environ, production=True)}
DATABASE_ROUTERS = ["apps.common.db_router.PendingSchemaApprovalRouter"]
REDIS_URL = required("REDIS_URL")
from apps.common.redis_backend import redis_target
redis_target(REDIS_URL)
CACHES["default"]["LOCATION"] = REDIS_URL
CACHES["default"]["BACKEND"] = "apps.common.redis_backend.RedisCache"
import re
REDIS_KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "ishchi:production")
if not re.fullmatch(r"ishchi:[a-z0-9_-]+", REDIS_KEY_PREFIX):
    raise ImproperlyConfigured("REDIS_KEY_PREFIX must be an explicit ishchi:<environment> namespace.")
CACHES["default"]["KEY_PREFIX"] = REDIS_KEY_PREFIX
CACHES["default"]["OPTIONS"].update({
    "SOCKET_CONNECT_TIMEOUT": 5, "SOCKET_TIMEOUT": 5,
    "CONNECTION_POOL_KWARGS": {"ssl_cert_reqs": "required", "ssl_check_hostname": True},
})
if os.environ.get("REDIS_SSLROOTCERT"):
    import ssl
    try:
        ssl.create_default_context(cafile=os.environ["REDIS_SSLROOTCERT"])
    except (OSError, ssl.SSLError):
        raise ImproperlyConfigured("REDIS_SSLROOTCERT must be a readable valid CA certificate.") from None
    CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"]["ssl_ca_certs"] = os.environ["REDIS_SSLROOTCERT"]
# Registration does not use SMS. Optional verification/password reset may use HTTP.
SMS_BACKEND = os.environ.get("SMS_BACKEND", "disabled")
if SMS_BACKEND not in {"disabled", "http"}:
    raise ImproperlyConfigured("Production SMS_BACKEND must be disabled or http; local providers are prohibited.")
if SMS_BACKEND == "http":
    SMS_API_URL = required("SMS_API_URL")
    SMS_API_TOKEN = required("SMS_API_TOKEN")
    parts = urlsplit(SMS_API_URL)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ImproperlyConfigured("Production SMS requires an HTTPS SMS_API_URL; no development fallback.")
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY
SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(minutes=15)
SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] = timedelta(days=7)
LOGGING["root"]["level"] = "WARNING"
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
if not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured("DJANGO_MEDIA_ROOT must be an absolute persistent storage path.")
# Only dependency-free liveness may use the loopback HTTP probe.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/live/$"]
