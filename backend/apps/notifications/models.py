from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedUUIDModel


class NotificationEventType(models.TextChoices):
    NEW_APPLICATION = "NEW_APPLICATION", "New Application"
    APPLICATION_ACCEPTED = "APPLICATION_ACCEPTED", "Application Accepted"
    APPLICATION_REJECTED = "APPLICATION_REJECTED", "Application Rejected"
    NEW_INVITATION = "NEW_INVITATION", "New Invitation"
    INVITATION_ACCEPTED = "INVITATION_ACCEPTED", "Invitation Accepted"
    INVITATION_REJECTED = "INVITATION_REJECTED", "Invitation Rejected"
    NEW_MESSAGE = "NEW_MESSAGE", "New Message"
    ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED", "Order Status Changed"
    NEW_REVIEW = "NEW_REVIEW", "New Review"
    VERIFICATION_UPDATED = "VERIFICATION_UPDATED", "Verification Updated"
    SYSTEM = "SYSTEM", "System"


class Notification(TimeStampedUUIDModel):
    """Real persisted user notification triggered by marketplace events."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(
        max_length=40,
        choices=NotificationEventType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"], name="idx_notif_recipient_read"),
        ]

    def __str__(self):
        return f"Notification({self.event_type} -> {self.recipient_id}, read={self.is_read})"
