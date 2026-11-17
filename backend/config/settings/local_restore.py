"""Read/rollback-only recovery verification. No server, working Redis or SMS."""
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403
from apps.common.local_targets import local_database, secret_file

if IS_PRODUCTION:
    raise ImproperlyConfigured("Local recovery settings cannot run in production.")
LOCAL_TARGET_KIND = "restore"
LOCAL_DEVELOPMENT = False
DEBUG = False
SECRET_KEY = secret_file(os.environ, "DJANGO_SECRET_KEY")
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
DATABASES = {"default": local_database(os.environ, "restore")}
CACHES = {"default":{"BACKEND":"django.core.cache.backends.locmem.LocMemCache"}}
SMS_BACKEND = "disabled"
PAYMENT_ENABLED = False
MEDIA_ROOT = Path(os.environ["DJANGO_MEDIA_ROOT"]).resolve()
_sandbox = Path(r"D:\Ishchi-restore-sandbox").resolve()
if _sandbox not in MEDIA_ROOT.parents or not MEDIA_ROOT.is_dir():
    raise ImproperlyConfigured("An existing isolated recovery sandbox media directory is required.")
