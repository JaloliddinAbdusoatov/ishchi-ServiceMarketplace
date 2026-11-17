"""Persistent localhost-only application. No migrations or seeding on startup."""
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403
from apps.common.local_targets import local_database, local_redis_url, secret_file

if IS_PRODUCTION:
    raise ImproperlyConfigured("Local PostgreSQL settings cannot be used in production mode.")
LOCAL_TARGET_KIND = "work"
LOCAL_DEVELOPMENT = True
DEBUG = False
SECRET_KEY = secret_file(os.environ, "DJANGO_SECRET_KEY")
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]
CORS_ALLOWED_ORIGINS = []  # Browser uses the same-origin nginx API proxy.
TRUSTED_PROXY_IPS = ["127.0.0.1"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
DATABASES = {"default": local_database(os.environ, "work")}
DATABASE_ROUTERS = []
REDIS_URL = local_redis_url(os.environ, "work")
CACHES = {"default": {"BACKEND": "apps.common.redis_backend.RedisCache", "LOCATION": REDIS_URL,
    "KEY_PREFIX": "ishchi:local:work", "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",
        "IGNORE_EXCEPTIONS": False, "SOCKET_CONNECT_TIMEOUT": 5, "SOCKET_TIMEOUT": 5}}}
SMS_BACKEND = os.environ.get("SMS_BACKEND", "disabled")
if SMS_BACKEND not in {"disabled", "http"}:
    raise ImproperlyConfigured("Local PostgreSQL permits disabled or explicitly configured HTTP SMS only.")
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / ".local" / "media")))
if not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured("Local media storage requires an absolute persistent path.")
