"""Reject protected targets before opening any PostgreSQL connection."""
import re
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLWrapper

def validate_target(params):
    name = str(params.get("dbname", ""))
    # Dedicated databases only: reject protected targets, libpq DSNs, and URIs.
    if not re.fullmatch(r"ishchi_marketplace(?:_[a-z0-9_]+)?", name):
        raise ImproperlyConfigured("Only a dedicated ishchi_marketplace database is permitted. Authoritative and system databases are prohibited.")
    if any(params.get(k) for k in ("service", "passfile", "database", "hostaddr")):
        raise ImproperlyConfigured("Database target overrides are prohibited.")
    for key in ("host", "user", "port"):
        if not params.get(key):
            raise ImproperlyConfigured(f"Explicit database {key} required; libpq environment fallback is prohibited.")

class DatabaseWrapper(PostgreSQLWrapper):
    def schema_editor(self, *args, **kwargs):
        raise ImproperlyConfigured("PostgreSQL schema deployment requires a separately approved migration plan.")

    def get_new_connection(self, conn_params):
        validate_target(conn_params)
        return super().get_new_connection(conn_params)
