import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q
from apps.common.models import TimeStampedUUIDModel
from apps.common.validators import UZ_PHONE_REGEX


class UserRole(models.TextChoices):
    WORKER = "WORKER", "Worker"
    EMPLOYER = "EMPLOYER", "Employer"
    ADMIN = "ADMIN", "Admin"


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    DELETED = "DELETED", "Deleted / Anonymized"


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, role=UserRole.WORKER, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required.")
        if not UZ_PHONE_REGEX.match(phone_number):
            raise ValueError("Phone number must match Uzbekistan format +998XXXXXXXXX.")

        email = extra_fields.pop("email", None)
        if email:
            email = self.normalize_email(email).strip() or None
        else:
            email = None

        has_worker_role = extra_fields.pop("has_worker_role", role == UserRole.WORKER)
        has_employer_role = extra_fields.pop("has_employer_role", role == UserRole.EMPLOYER)

        user = self.model(
            phone_number=phone_number,
            email=email,
            role=role,
            has_worker_role=has_worker_role,
            has_employer_role=has_employer_role,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_phone_verified", True)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)
        extra_fields.setdefault("has_worker_role", False)
        extra_fields.setdefault("has_employer_role", False)

        if not password:
            raise ValueError("Superuser must have a password.")
        return self.create_user(phone_number=phone_number, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedUUIDModel):
    """
    Custom User model supporting WORKER, EMPLOYER, ADMIN roles,
    dual Worker+Employer capability without duplicate accounts,
    token_version revocation, and GDPR-compliant anonymization.
    """

    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True, default="")
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.WORKER,
        db_index=True,
    )
    has_worker_role = models.BooleanField(default=False, db_index=True)
    has_employer_role = models.BooleanField(default=False, db_index=True)

    is_phone_verified = models.BooleanField(default=False)
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)

    token_version = models.PositiveIntegerField(default=1)

    is_anonymized = models.BooleanField(default=False, db_index=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=Q(email__isnull=False),
                name="uq_accounts_user_email_non_null",
            ),
            models.CheckConstraint(
                condition=Q(email__isnull=True) | ~Q(email=""),
                name="chk_accounts_user_email_not_empty",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_anonymized=False, phone_number__isnull=False, phone_number__regex=r"^\+998[0-9]{9}$")
                    | Q(is_anonymized=True, phone_number__isnull=True)
                ),
                name="chk_accounts_user_phone_anonymization",
            ),
        ]
        indexes = [
            models.Index(fields=["role", "account_status"], name="idx_user_role_status"),
        ]

    def __str__(self):
        if self.is_anonymized:
            return f"Anonymized User ({self.id})"
        return f"{self.phone_number} ({self.role})"

    @property
    def is_worker(self) -> bool:
        return bool(self.has_worker_role or self.role == UserRole.WORKER)

    @property
    def is_employer(self) -> bool:
        return bool(self.has_employer_role or self.role == UserRole.EMPLOYER)

    @property
    def is_admin_user(self) -> bool:
        return bool(self.role == UserRole.ADMIN and self.is_staff)

    @property
    def is_verified_worker(self) -> bool:
        if not self.is_worker:
            return False
        profile = getattr(self, "worker_profile", None)
        return bool(profile and profile.is_verified and profile.verification_status == "VERIFIED")


class AccountDeletionAudit(models.Model):
    """Immutable audit log created whenever an account is deleted and anonymized."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    phone_hash = models.CharField(max_length=64)
    role = models.CharField(max_length=20)
    reason = models.TextField(blank=True, default="")
    performed_by_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_deletion_audit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DeletionAudit({self.user_id} at {self.created_at})"
