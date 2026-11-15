from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.categories.models import Category
from apps.common.models import TimeStampedUUIDModel
from apps.common.validators import validate_image_file
from apps.profiles.models import EmployerProfile, WorkerProfile


class BudgetType(models.TextChoices):
    FIXED = "FIXED", "Fixed Price"
    HOURLY = "HOURLY", "Hourly Rate"
    NEGOTIABLE = "NEGOTIABLE", "Negotiable"


class WorkType(models.TextChoices):
    ONSITE = "ONSITE", "On-site"
    REMOTE = "REMOTE", "Remote"
    HYBRID = "HYBRID", "Hybrid"


class OrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    PAUSED = "PAUSED", "Paused"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    CLOSED = "CLOSED", "Closed"


class PaymentStatus(models.TextChoices):
    DISABLED = "DISABLED", "Payments unavailable"


class ServiceOrder(TimeStampedUUIDModel):
    """Marketplace service order created by an employer."""

    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="orders",
    )
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )
    capacity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(50)])
    assigned_workers = models.ManyToManyField(WorkerProfile, blank=True, related_name="team_orders")
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    budget = models.DecimalField(max_digits=14, decimal_places=2, db_index=True)
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.FIXED,
        db_index=True,
    )
    location = models.CharField(max_length=120, db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    address = models.CharField(max_length=255, blank=True, default="")
    work_type = models.CharField(
        max_length=20,
        choices=WorkType.choices,
        default=WorkType.ONSITE,
        db_index=True,
    )
    deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.DISABLED,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders_service_order"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1, capacity__lte=50), name="chk_order_capacity_range"),
            models.CheckConstraint(
                condition=Q(budget__gt=0),
                name="chk_order_budget_positive",
            ),
            models.CheckConstraint(
                condition=Q(payment_status=PaymentStatus.DISABLED),
                name="chk_order_payment_disabled_demo",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "category", "created_at"], name="idx_order_browse"),
            models.Index(fields=["location", "district", "status"], name="idx_order_location"),
            models.Index(fields=["employer", "status"], name="idx_order_employer_status"),
        ]

    def __str__(self):
        return f"ServiceOrder({self.title} [{self.status}])"

    def get_hired_workers(self):
        workers = list(self.assigned_workers.select_related("user").all())
        if self.assigned_worker_id and not any(w.pk == self.assigned_worker_id for w in workers):
            workers.append(self.assigned_worker)
        return workers

    @property
    def hired_worker_count(self):
        return len(self.get_hired_workers())


class OrderImage(TimeStampedUUIDModel):
    """Photo attachments associated with a ServiceOrder."""

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="orders/images/",
        validators=[validate_image_file],
    )
    caption = models.CharField(max_length=200, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "orders_order_image"
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"OrderImage({self.order_id})"
