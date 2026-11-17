import uuid
from django.db import models
from django.utils import timezone


class TimeStampedUUIDModel(models.Model):
    """Abstract base model with UUID primary key and audit timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MediaDeletionTask(TimeStampedUUIDModel):
    """Durable erasure outbox; file names are private operational data."""
    name = models.CharField(max_length=500, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name"], condition=models.Q(completed_at__isnull=True),
            name="uq_pending_media_erasure")]
