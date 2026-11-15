"""Single-process local development; ignores PostgreSQL/Redis environment targets."""
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403

if IS_PRODUCTION:
    raise ImproperlyConfigured("ISHCHI_ENV=production requires config.settings.production.")
INSTALLED_APPS = [*INSTALLED_APPS, "local_tools"]
DEBUG = True
LOCAL_DEVELOPMENT = True
LOCAL_SQLITE_DEMO = True  # Internal compatibility flag for existing tooling.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
LOCAL_DIR = BASE_DIR / ".local"
LOCAL_DIR.mkdir(exist_ok=True)
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": LOCAL_DIR / "ishchi.sqlite3",
    "OPTIONS": {"timeout": 30, "transaction_mode": "IMMEDIATE"}, "TEST": {"NAME": ":memory:"},
}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "ishchi-local"}}
MEDIA_ROOT = LOCAL_DIR / "media"
# Absent an explicit provider, development also fails closed.
SMS_BACKEND = os.environ.get("SMS_BACKEND", "disabled")
