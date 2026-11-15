from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import TimeStampedUUIDModel
from apps.common.validators import validate_chat_attachment
from apps.orders.models import ServiceOrder
from apps.profiles.models import EmployerProfile, WorkerProfile


class Conversation(TimeStampedUUIDModel):
    """Order-scoped conversation between the order's employer and an applicant worker."""

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "chat_conversation"
        ordering = ["-last_message_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "worker"],
                name="uq_conversation_order_worker",
            ),
        ]
        indexes = [
            models.Index(fields=["employer", "last_message_at"], name="idx_conv_employer_last"),
            models.Index(fields=["worker", "last_message_at"], name="idx_conv_worker_last"),
        ]

    def __str__(self):
        return f"Conversation(order={self.order_id}, worker={self.worker_id})"


class Message(TimeStampedUUIDModel):
    """Message inside a Conversation with optional validated attachment."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField(blank=True, default="")
    attachment = models.FileField(
        upload_to="chat/attachments/",
        null=True,
        blank=True,
        validators=[validate_chat_attachment],
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(content="") | (Q(attachment__isnull=False) & ~Q(attachment="")),
                name="chk_chat_message_not_empty",
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="idx_msg_conv_created"),
            models.Index(fields=["conversation", "is_read"], name="idx_msg_conv_read"),
        ]

    def __str__(self):
        return f"Message({self.id} in {self.conversation_id})"
