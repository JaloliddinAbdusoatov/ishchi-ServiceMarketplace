"""Static collection only: no services, local environment or runtime fallback."""
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403
if IS_PRODUCTION:
    raise ImproperlyConfigured("Static-build settings cannot run in production mode.")
SECRET_KEY = "public-static-build-placeholder-not-a-runtime-secret"
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
DEBUG = False
