import pytest
from django.conf import settings


def pytest_configure(config):
    if config.option.collectonly:
        return
    if any(database["ENGINE"] != "django.db.backends.sqlite3" for database in settings.DATABASES.values()):
        raise pytest.UsageError("Redis tests require --ds=config.settings.testing; do not combine PostgreSQL and Redis runtime suites.")
