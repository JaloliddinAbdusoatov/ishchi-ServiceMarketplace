"""Offline preflight branch tests; mocked metadata is not PostgreSQL verification."""
from unittest.mock import MagicMock
import pytest
from django.core.exceptions import ImproperlyConfigured
from pgtests.safety import verify_database


@pytest.mark.parametrize("unsafe", ["identity", "privileges", "database_owner", "schema_owner", "other_schema", "occupied"])
def test_preflight_rejects_unsafe_disposable_target(unsafe):
    connection = MagicMock()
    connection.settings_dict = {"NAME": "ishchi_marketplace_sprint1_offline", "USER": "migration_owner"}
    identity = (connection.settings_dict["NAME"], "migration_owner", "public")
    rows = [identity, (False,), (True,), (True,), (False,), (False,)]
    if unsafe == "identity":
        rows[0] = ("unapproved_database", "migration_owner", "public")
    else:
        index = {"privileges": 1, "database_owner": 2, "schema_owner": 3, "other_schema": 4, "occupied": 5}[unsafe]
        rows[index] = (not rows[index][0],)
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = rows
    with pytest.raises(ImproperlyConfigured):
        verify_database(connection)
    assert all(str(call.args[0]).lstrip().startswith("SELECT") for call in cursor.execute.call_args_list)


def test_preflight_accepts_expected_owner_and_empty_schema_offline():
    connection = MagicMock()
    connection.settings_dict = {"NAME": "ishchi_marketplace_sprint1_offline", "USER": "migration_owner"}
    connection.cursor.return_value.__enter__.return_value.fetchone.side_effect = [
        (connection.settings_dict["NAME"], "migration_owner", "public"), (False,), (True,), (True,), (False,), (False,)]
    verify_database(connection)
