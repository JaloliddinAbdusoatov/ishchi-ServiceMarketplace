from django.utils import timezone
from apps.notifications.models import Notification, NotificationEventType


class NotificationService:
    """Persists real-time user notifications triggered by marketplace domain events."""

    @staticmethod
    def notify(recipient, event_type: str, title: str, message: str, data: dict = None) -> Notification:
        if getattr(recipient, "is_anonymized", False):
            return None
        return Notification.objects.create(
            recipient=recipient,
            event_type=event_type,
            title=title,
            message=message,
            data=data or {},
        )

    @staticmethod
    def mark_read(notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    def mark_all_read(user) -> int:
        now = timezone.now()
        return Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=now,
            updated_at=now,
        )
