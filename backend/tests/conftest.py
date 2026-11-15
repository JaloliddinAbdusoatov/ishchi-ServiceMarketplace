from decimal import Decimal
import factory
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import AccountStatus, User, UserRole
from apps.accounts.services.auth_service import generate_jwt_pair
from apps.categories.models import Category
from apps.orders.models import BudgetType, OrderStatus, ServiceOrder, WorkType
from apps.profiles.models import EmployerProfile, EmployerType, VerificationStatus, WorkerProfile


def pytest_configure(config):
    """Refuse unsafe environment overrides before any test database is created."""
    from django.conf import settings
    for config in settings.DATABASES.values():
        if config["ENGINE"] != "django.db.backends.sqlite3" or "ishchi_test" in str(config["NAME"]).lower():
            raise pytest.UsageError("Teacher demo tests require --ds=config.settings.testing (SQLite only).")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    phone_number = factory.Sequence(lambda n: f"+99891{n + 1000000:07d}")
    full_name = factory.Faker("name")
    role = UserRole.WORKER
    has_worker_role = True
    has_employer_role = False
    is_phone_verified = True
    account_status = AccountStatus.ACTIVE
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "StrongPass2026!")
        obj = super()._create(model_class, *args, **kwargs)
        obj.set_password(password)
        obj.save(update_fields=["password"])
        return obj


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    slug = factory.Sequence(lambda n: f"category-{n}")
    name = factory.Sequence(lambda n: f"Kategoriya {n}")
    name_uz = factory.LazyAttribute(lambda o: o.name)
    name_ru = factory.LazyAttribute(lambda o: f"{o.name} RU")
    name_en = factory.LazyAttribute(lambda o: f"{o.name} EN")
    is_active = True


_redis_available = None

@pytest.fixture(autouse=True)
def clear_redis_cache():
    global _redis_available
    if _redis_available is not False:
        try:
            cache.clear()
            _redis_available = True
        except Exception:
            _redis_available = False
    yield
    if _redis_available is True:
        try:
            cache.clear()
        except Exception:
            _redis_available = False


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client():
    def _make(user: User) -> APIClient:
        client = APIClient()
        tokens = generate_jwt_pair(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return client
    return _make


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        phone_number="+998909990001",
        password="AdminPass2026!",
        full_name="Test Admin",
    )


@pytest.fixture
def verified_worker(db):
    user = UserFactory(
        phone_number="+998908880001",
        full_name="Jasur Verified",
        role=UserRole.WORKER,
        has_worker_role=True,
        has_employer_role=False,
    )
    profile = WorkerProfile.objects.create(
        user=user,
        full_name=user.full_name,
        phone_number=user.phone_number,
        location="Toshkent",
        district="Chilonzor",
        experience_years=5,
        is_verified=True,
        verification_status=VerificationStatus.VERIFIED,
    )
    return user, profile


@pytest.fixture
def unverified_worker(db):
    user = UserFactory(
        phone_number="+998908880002",
        full_name="Otabek Unverified",
        role=UserRole.WORKER,
        has_worker_role=True,
        has_employer_role=False,
    )
    profile = WorkerProfile.objects.create(
        user=user,
        full_name=user.full_name,
        phone_number=user.phone_number,
        location="Toshkent",
        district="Yunusobod",
        experience_years=2,
        is_verified=False,
        verification_status=VerificationStatus.UNSUBMITTED,
    )
    return user, profile


@pytest.fixture
def employer_pair(db):
    user = UserFactory(
        phone_number="+998907770001",
        full_name="Azizbek Employer",
        role=UserRole.EMPLOYER,
        has_worker_role=False,
        has_employer_role=True,
    )
    profile = EmployerProfile.objects.create(
        user=user,
        employer_type=EmployerType.INDIVIDUAL,
        full_name=user.full_name,
        phone_number=user.phone_number,
        location="Toshkent",
        district="Chilonzor",
    )
    return user, profile


@pytest.fixture
def active_category(db):
    return CategoryFactory(slug="plumbing-test", name="Santexnika Test")


@pytest.fixture
def published_order(db, employer_pair, active_category):
    _, emp_profile = employer_pair
    return ServiceOrder.objects.create(
        employer=emp_profile,
        category=active_category,
        title="Quvur ta'mirlash",
        description="Hammom quvurini almashtirish kerak",
        budget=Decimal("500000.00"),
        budget_type=BudgetType.FIXED,
        location="Toshkent",
        district="Chilonzor",
        work_type=WorkType.ONSITE,
        status=OrderStatus.PUBLISHED,
    )
