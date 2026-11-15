from datetime import timedelta
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import ServiceOrder
from apps.profiles.models import EmployerProfile, WorkerProfile


class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class OrderInvitation(TimeStampedUUIDModel):
    """Direct employer invitation sent to a verified worker for a ServiceOrder."""

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="received_invitations",
    )
    message = models.TextField(blank=True, default="")
    proposed_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField(default=default_invitation_expiry, db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invitations_order_invitation"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(proposed_budget__isnull=True) | Q(proposed_budget__gt=0),
                name="chk_inv_proposed_budget_positive",
            ),
            models.UniqueConstraint(
                fields=["order", "worker"],
                condition=Q(status__in=[InvitationStatus.PENDING, InvitationStatus.ACCEPTED]),
                name="uq_active_order_worker_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["worker", "status"], name="idx_inv_worker_status"),
            models.Index(fields=["order", "status"], name="idx_inv_order_status"),
        ]

    def __str__(self):
        return f"Invitation({self.order.title} -> {self.worker.full_name} [{self.status}])"
