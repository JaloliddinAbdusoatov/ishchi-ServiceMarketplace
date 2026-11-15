from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import TimeStampedUUIDModel
from apps.common.validators import validate_image_file


class PricingPreference(models.TextChoices):
    HOURLY = "HOURLY", "Hourly"
    FIXED = "FIXED", "Fixed"
    NEGOTIABLE = "NEGOTIABLE", "Negotiable"


class VerificationStatus(models.TextChoices):
    UNSUBMITTED = "UNSUBMITTED", "Unsubmitted"
    PENDING = "PENDING", "Pending Admin Review"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class EmployerType(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    COMPANY = "COMPANY", "Company"


class WorkerProfile(TimeStampedUUIDModel):
    """Worker marketplace profile with admin-controlled verification status."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="worker_profile",
    )
    full_name = models.CharField(max_length=150, db_index=True)
    bio = models.TextField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    photo = models.ImageField(
        upload_to="workers/photos/",
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    location = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    skills = models.JSONField(default=list, blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0, db_index=True)
    experience_description = models.TextField(blank=True, default="")
    pricing_type = models.CharField(
        max_length=20,
        choices=PricingPreference.choices,
        default=PricingPreference.NEGOTIABLE,
        db_index=True,
    )
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fixed_rate_from = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True, db_index=True)

    # Admin-controlled verification fields (never writable by workers)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNSUBMITTED,
        db_index=True,
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    verification_notes = models.TextField(blank=True, default="")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_workers",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Aggregated metrics
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
    )
    review_count = models.PositiveIntegerField(default=0)
    completed_orders_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "profiles_worker"
        ordering = ["-is_verified", "-rating_avg", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(verification_status=VerificationStatus.VERIFIED, is_verified=True)
                    | (~Q(verification_status=VerificationStatus.VERIFIED) & Q(is_verified=False))
                ),
                name="chk_worker_verification_sync",
            ),
            models.CheckConstraint(
                condition=Q(hourly_rate__isnull=True) | Q(hourly_rate__gte=0),
                name="chk_worker_hourly_rate_non_neg",
            ),
            models.CheckConstraint(
                condition=Q(fixed_rate_from__isnull=True) | Q(fixed_rate_from__gte=0),
                name="chk_worker_fixed_rate_non_neg",
            ),
            models.CheckConstraint(
                condition=Q(rating_avg__gte=0) & Q(rating_avg__lte=5),
                name="chk_worker_rating_range",
            ),
        ]
        indexes = [
            models.Index(fields=["location", "district"], name="idx_worker_loc_district"),
            models.Index(fields=["is_verified", "is_available", "rating_avg"], name="idx_worker_discovery"),
        ]

    def __str__(self):
        return f"WorkerProfile({self.full_name}, verified={self.is_verified})"


class WorkerPortfolioItem(TimeStampedUUIDModel):
    """Portfolio showcase item belonging to a worker."""

    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="portfolio_items",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(
        upload_to="workers/portfolio/",
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    project_url = models.URLField(blank=True, default="")
    completed_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "profiles_worker_portfolio"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.worker.full_name})"


class EmployerProfile(TimeStampedUUIDModel):
    """Employer (individual or company) marketplace profile."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employer_profile",
    )
    employer_type = models.CharField(
        max_length=20,
        choices=EmployerType.choices,
        default=EmployerType.INDIVIDUAL,
        db_index=True,
    )
    full_name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=200, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(max_length=255, null=True, blank=True)
    photo = models.ImageField(
        upload_to="employers/photos/",
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    location = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    address = models.CharField(max_length=255, blank=True, default="")

    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    review_count = models.PositiveIntegerField(default=0)
    posted_orders_count = models.PositiveIntegerField(default=0)
    completed_orders_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "profiles_employer"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating_avg__gte=0) & Q(rating_avg__lte=5),
                name="chk_employer_rating_range",
            ),
        ]

    def __str__(self):
        label = self.company_name if self.employer_type == EmployerType.COMPANY and self.company_name else self.full_name
        return f"EmployerProfile({label})"
