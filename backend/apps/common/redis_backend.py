"""Redis authorization gate; checking configuration never opens a socket."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django_redis.cache import RedisCache as DjangoRedisCache
from redis.connection import parse_url


def redis_target(url, *, allow_local=False):
    """Match redis-py's decoded transport identity, without creating a client."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ({"redis", "rediss"} if allow_local else {"rediss"}) or not parts.hostname or parts.query or parts.fragment or not parts.path.lstrip("/").isdigit():
            raise ValueError()
        parsed = parse_url(url)
        if not parsed.get("username") or not parsed.get("password"):
            raise ValueError()
        return {"host": parsed["host"], "port": parsed.get("port", 6379),
                "database": parsed["db"], "user": parsed["username"]}
    except (ValueError, KeyError, TypeError):
        raise ImproperlyConfigured("Redis requires a single rediss://user:password@host:port/database URL without overrides.") from None


def authorize_redis(url, operation="cache"):
    if getattr(settings, "IS_PRODUCTION", False):
        raise ImproperlyConfigured(
            "Production Redis access is blocked: local attestations cannot grant owner authority. "
            "A separately reviewed deployment authorization mechanism is required."
        )
    try:
        kind = getattr(settings, "LOCAL_TARGET_KIND", "")
        target = redis_target(url, allow_local=bool(kind))
        if kind:
            from .local_targets import validate_local_redis
            validate_local_redis(target, kind)
        approval = json.loads(Path(os.environ["REDIS_AUTHORIZATION_FILE"]).read_text(encoding="utf-8"))
        expires = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
        if not (approval["target"] == target and approval["approved_by"].strip()
                and expires > datetime.now(timezone.utc) and isinstance(approval["operations"], list)
                and operation in approval["operations"]):
            raise ValueError()
        if operation == "cache_test" and approval.get("disposable") is not True:
            raise ValueError()
    except (OSError, KeyError, ValueError, TypeError, AttributeError):
        raise ImproperlyConfigured("Explicit unexpired REDIS_AUTHORIZATION_FILE approval for this target is required.") from None


class RedisCache(DjangoRedisCache):
    @property
    def client(self):
        if isinstance(self._server, (list, tuple)):
            if len(self._server) != 1:
                raise ImproperlyConfigured("Only one explicitly approved Redis endpoint is supported.")
            server = self._server[0]
        else:
            server = self._server
        authorize_redis(server)
        return super().client

    def close(self, **kwargs):
        # Closing existing clients needs no new authorization or connection.
        if self._client is not None:
            self._client.close(**kwargs)
