"""No database creation, cloning, or maintenance-database connection."""
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection, connections
from apps.common.db_authorization import authorize
from .safety import verify_database
from tests.conftest import (  # noqa: F401 -- explicitly share fixtures, not plugin registration
    api_client, auth_client, admin_user, verified_worker, unverified_worker,
    employer_pair, active_category, published_order, clear_redis_cache,
)

def pytest_configure(config):
    if config.option.collectonly:
        return
    if not getattr(settings, "POSTGRES_INTEGRATION", False):
        raise pytest.UsageError("PostgreSQL tests require --ds=config.settings.postgres_integration.")
    if getattr(config.option, "reuse_db", False) or getattr(config.option, "create_db", False) or getattr(config.option, "numprocesses", None):
        raise pytest.UsageError("Database creation/reuse and xdist are prohibited for this harness.")
    params = connection.get_connection_params()
    authorize(params, "connect")
    authorize(params, "test_schema")


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    if not getattr(settings, "POSTGRES_INTEGRATION", False):
        raise pytest.UsageError("Use --ds=config.settings.postgres_integration after explicit authorization.")
    try:
        with django_db_blocker.unblock():
            verify_database(connection)
            call_command("migrate", interactive=False, verbosity=0)
        yield
    finally:
        connections.close_all()
