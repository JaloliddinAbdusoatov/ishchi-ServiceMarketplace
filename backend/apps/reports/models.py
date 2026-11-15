from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.chat.models import Message
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import ServiceOrder


class ReportTargetType(models.TextChoices):
    USER = "USER", "User"
    ORDER = "ORDER", "Order"
    MESSAGE = "MESSAGE", "Message"


class ReportReason(models.TextChoices):
    SPAM = "SPAM", "Spam"
    FRAUD = "FRAUD", "Fraud / Scam"
    INAPPROPRIATE = "INAPPROPRIATE", "Inappropriate Content"
    HARASSMENT = "HARASSMENT", "Harassment"
    FAKE_PROFILE = "FAKE_PROFILE", "Fake Profile"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"


class Report(TimeStampedUUIDModel):
    """User-submitted moderation report against a user, order, or chat message."""

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
    )
    target_type = models.CharField(
        max_length=20,
        choices=ReportTargetType.choices,
        db_index=True,
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_against",
    )
    target_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    target_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    reason = models.CharField(max_length=30, choices=ReportReason.choices)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    admin_resolution = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_reports",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reports_report"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(target_type=ReportTargetType.USER, target_user__isnull=False, target_order__isnull=True, target_message__isnull=True)
                    | Q(target_type=ReportTargetType.ORDER, target_order__isnull=False, target_user__isnull=True, target_message__isnull=True)
                    | Q(target_type=ReportTargetType.MESSAGE, target_message__isnull=False, target_user__isnull=True, target_order__isnull=True)
                ),
                name="chk_report_exactly_one_target",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_report_status_created"),
        ]

    def __str__(self):
        return f"Report({self.target_type} [{self.status}])"
