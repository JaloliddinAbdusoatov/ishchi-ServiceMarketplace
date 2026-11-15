"""Offline tests: in-memory SQLite, no environment database targets."""
from .development import *  # noqa: F403
DATABASES["default"]["NAME"] = ":memory:"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SMS_BACKEND = "memory"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
