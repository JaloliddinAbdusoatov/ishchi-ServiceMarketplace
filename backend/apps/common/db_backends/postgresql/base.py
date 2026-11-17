"""Reject protected targets before opening any PostgreSQL connection."""
import re
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLWrapper
from django.db.backends.postgresql.creation import DatabaseCreation as PostgreSQLCreation


class ExplicitDatabaseCreation(PostgreSQLCreation):
    def create_test_db(self, *args, **kwargs):
        raise ImproperlyConfigured("Automatic PostgreSQL database creation is prohibited; use the pre-provisioned integration harness.")

    def clone_test_db(self, *args, **kwargs):
        raise ImproperlyConfigured("Automatic PostgreSQL database cloning is prohibited.")

    def destroy_test_db(self, *args, **kwargs):
        raise ImproperlyConfigured("Automatic PostgreSQL database destruction is prohibited.")

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
    if any(value for key, value in os.environ.items() if key.startswith("PG")):
        raise ImproperlyConfigured("Clear libpq PG* environment overrides before PostgreSQL use.")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", str(params["host"])):
        raise ImproperlyConfigured("Use one explicit PostgreSQL hostname or IP.")

class DatabaseWrapper(PostgreSQLWrapper):
    creation_class = ExplicitDatabaseCreation

    def schema_editor(self, *args, **kwargs):
        purpose = getattr(settings, "LOCAL_TARGET_KIND", "")
        if purpose == "work":
            raise ImproperlyConfigured("Runtime schema changes are prohibited; use the separately approved local migration operator.")
        local_migration = purpose == "migration"
        if not getattr(settings, "POSTGRES_INTEGRATION", False) and not local_migration:
            raise ImproperlyConfigured("PostgreSQL schema deployment requires a separately approved migration plan.")
        from apps.common.db_authorization import authorize
        params = self.get_connection_params()
        validate_target(params)
        authorize(params, "local_migrate" if local_migration else "test_schema")
        return super().schema_editor(*args, **kwargs)

    def get_new_connection(self, conn_params):
        validate_target(conn_params)
        from apps.common.db_authorization import authorize
        authorize(conn_params)
        return super().get_new_connection(conn_params)
