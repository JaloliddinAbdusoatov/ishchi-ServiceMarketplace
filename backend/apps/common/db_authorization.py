"""Integration target interlock, not an owner-approval authority."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


def authorize(params, operation="connect"):
    if getattr(settings, "IS_PRODUCTION", False):
        raise ImproperlyConfigured(
            "Production database access is blocked: local attestations cannot grant owner authority. "
            "A separately reviewed deployment authorization mechanism is required."
        )
    kind = getattr(settings, "LOCAL_TARGET_KIND", "")
    if kind:
        from .local_targets import validate_local_pg
        validate_local_pg(params, kind)
    if operation == "test_schema" and kind == "work":
        raise ImproperlyConfigured("Integration schema operations are forbidden on the persistent local database.")
    try:
        document = json.loads(Path(os.environ["DB_AUTHORIZATION_FILE"]).read_text(encoding="utf-8"))
        target = {key: str(params[key]) for key in ("dbname", "host", "port", "user")}
        expires = datetime.fromisoformat(document["expires_at"].replace("Z", "+00:00"))
        allowed = (
            document["target"] == target
            and bool(document["approved_by"].strip())
            and expires > datetime.now(timezone.utc)
            and isinstance(document["operations"], list)
            and operation in document["operations"]
        )
        if operation == "test_schema":
            allowed = allowed and document.get("disposable") is True
        if not allowed:
            raise ValueError("Authorization does not cover this operation")
    except (OSError, KeyError, ValueError, TypeError, AttributeError):
        raise ImproperlyConfigured(
            f"Explicit, unexpired DB_AUTHORIZATION_FILE approval for {operation} on this exact target is required."
        ) from None
