"""Execute existing real API/ORM scenarios on the authorized PostgreSQL target."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from tests.test_orders_applications_invitations import TestOrdersApplicationsInvitations as _OrderScenarios

from tests.test_teacher_finish_flow import (
    test_registered_unverified_team_to_chat_completion_reviews_and_admin,
    test_invitation_alone_never_grants_chat,
    test_category_limits_are_enforced_by_api_and_sqlite as test_category_limits_api_and_database,
    test_partial_team_rejects_double_hiring_across_application_and_invitation,
)
from tests.test_production_mvp import (
    test_registration_activates_immediately_without_sms_or_admin_approval,
    test_disabled_accounts_cannot_login_refresh_or_access,
    test_account_update_and_role_endpoint_cannot_grant_admin,
    test_django_admin_uses_real_account_boundaries,
)


@pytest.mark.django_db
def test_initial_migration_completes_on_empty_database():
    assert connection.vendor == "postgresql"
    executor = MigrationExecutor(connection)
    assert executor.migration_plan(executor.loader.graph.leaf_nodes()) == []


@pytest.mark.django_db
def test_draft_publication_pause_and_filtering(auth_client, employer_pair, active_category):
    _OrderScenarios().test_employer_order_lifecycle_and_filtering(auth_client, employer_pair, active_category)
