from django.db import models
from django.db.models import Q
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile


class ApplicationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class OrderApplication(TimeStampedUUIDModel):
    """Worker bid / application submitted to a published ServiceOrder."""

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    cover_message = models.TextField()
    proposed_price = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "applications_order_application"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(proposed_price__gt=0),
                name="chk_app_proposed_price_positive",
            ),
            models.UniqueConstraint(
                fields=["order", "worker"],
                condition=Q(status__in=[ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED]),
                name="uq_active_order_worker_application",
            ),
        ]
        indexes = [
            models.Index(fields=["order", "status"], name="idx_app_order_status"),
            models.Index(fields=["worker", "status"], name="idx_app_worker_status"),
        ]

    def __str__(self):
        return f"Application({self.worker.full_name} -> {self.order.title} [{self.status}])"
