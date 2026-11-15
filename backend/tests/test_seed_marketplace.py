import io
import json
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count, Q
from django.test import override_settings

from apps.accounts.models import User
from apps.categories.models import Category, WorkerCategory
from apps.chat.models import Message
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile
from apps.reviews.models import Review
from tests.conftest import UserFactory


def test_seed_rejects_production_before_database_access():
    with override_settings(IS_PRODUCTION=True, DEBUG=True):
        with pytest.raises(CommandError, match="local SQLite"):
            call_command("seed_marketplace")


def test_seed_rejects_other_sqlite_files_before_database_access(settings, tmp_path):
    settings.DEBUG = True
    settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(tmp_path / "other.sqlite3")}}
    with pytest.raises(CommandError, match=".local/ishchi.sqlite3"):
        call_command("seed_marketplace")


@pytest.mark.django_db
def test_random_content_is_additive_and_never_creates_admins(admin_user):
    existing_user = UserFactory()
    existing_name = existing_user.full_name
    output = io.StringIO()
    with override_settings(DEBUG=True), patch.object(User.objects, "create_superuser") as create_admin, patch(
        "apps.accounts.services.otp_service.get_sms_provider"
    ) as sms:
        call_command("seed_marketplace", workers=6, employers=2, orders=10, stdout=output)
        create_admin.assert_not_called()
        sms.assert_not_called()
    result = json.loads(output.getvalue())
    assert result["admins_created"] == 0
    assert result["created"]["users"] == 8
    assert result["created"]["categories"] == 24
    assert result["created"]["orders"] == 10
    assert result["created"]["applications"] == 27
    assert result["created"]["invitations"] == 9
    assert result["created"]["conversations"] == 9
    assert Message.objects.count() == 18
    assert Review.objects.count() == 6
    assert User.objects.filter(Q(role="ADMIN") | Q(is_staff=True) | Q(is_superuser=True)).count() == 1
    assert User.objects.get(pk=existing_user.pk).full_name == existing_name
    created_users = User.objects.filter(email__endswith="@example.invalid")
    assert all(not user.has_usable_password() and not user.is_phone_verified for user in created_users)
    assert not WorkerProfile.objects.filter(is_verified=True).exists()
    assert not WorkerCategory.objects.values("worker_id").annotate(n=Count("pk")).filter(n__gt=10).exists()
    assert set(ServiceOrder.objects.values_list("status", flat=True)) == {"DRAFT", "PUBLISHED", "PAUSED", "IN_PROGRESS", "COMPLETED"}
    assert all(order.hired_worker_count <= order.capacity for order in ServiceOrder.objects.all())
    assert all(profile.review_count == Review.objects.filter(reviewee=profile.user).count() for profile in WorkerProfile.objects.all())
    # Running again appends records and reuses the taxonomy instead of clearing data.
    with override_settings(DEBUG=True):
        call_command("seed_marketplace", workers=4, employers=1, orders=1, stdout=io.StringIO())
    assert Category.objects.count() == 24
    assert ServiceOrder.objects.count() == 11
    assert User.objects.filter(Q(role="ADMIN") | Q(is_staff=True) | Q(is_superuser=True)).count() == 1
