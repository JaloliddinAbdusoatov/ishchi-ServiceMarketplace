"""Retryable default-storage erasure without exposing filenames in logs."""
from datetime import timedelta
from functools import partial
import logging
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.utils import timezone
from apps.common.models import MediaDeletionTask

logger = logging.getLogger(__name__)
ALLOWED_PREFIXES = ("workers/photos/", "workers/portfolio/", "employers/photos/")


def validate_name(name):
    if not name.startswith(ALLOWED_PREFIXES) or any(part in ("", ".", "..") for part in name.split("/")) \
            or any(char in name for char in ("\\", ":", "\x00", "\r", "\n")):
        raise ValueError("Invalid erasure storage key")


def queue_media_erasure(names):
    if not connection.in_atomic_block:
        raise RuntimeError("Erasure tasks must be created in the anonymization transaction")
    ids = []
    for name in sorted(set(names)):
        validate_name(name)
        task, _ = MediaDeletionTask.objects.get_or_create(name=name, completed_at=None)
        ids.append(task.pk)
    if ids:
        transaction.on_commit(partial(process_media_erasure, task_ids=ids), robust=True)


def process_media_erasure(*, task_ids=None, limit=100):
    from apps.profiles.models import EmployerProfile, WorkerPortfolioItem, WorkerProfile
    if not 1 <= limit <= 1000:
        raise ValueError("Erasure batch limit must be between 1 and 1000")
    due = MediaDeletionTask.objects.filter(completed_at=None, next_attempt_at__lte=timezone.now())
    if task_ids is not None:
        due = due.filter(pk__in=task_ids)
    ids = list(due.order_by("next_attempt_at").values_list("pk", flat=True)[:limit])
    completed = failed = 0
    for task_id in ids:
        with transaction.atomic():
            task = MediaDeletionTask.objects.select_for_update(
                skip_locked=connection.features.has_select_for_update_skip_locked
            ).filter(pk=task_id, completed_at=None, next_attempt_at__lte=timezone.now()).first()
            if task is None:
                continue
            try:
                validate_name(task.name)
                referenced = (WorkerProfile.objects.filter(photo=task.name).exists()
                    or EmployerProfile.objects.filter(photo=task.name).exists()
                    or WorkerPortfolioItem.objects.filter(image=task.name).exists())
                # Never delete a key now referenced by a different/live profile.
                if not referenced:
                    default_storage.delete(task.name)
                task.completed_at = timezone.now()
                task.error_code = "referenced_media_preserved" if referenced else ""
                task.name = ""  # Completed outbox rows must not retain erased PII in filenames.
                completed += 1
            except Exception as exc:
                task.error_code = type(exc).__name__[:100]
                task.next_attempt_at = timezone.now() + timedelta(seconds=min(86400, 60 * 2 ** min(task.attempts, 10)))
                failed += 1
                logger.warning("Media erasure deferred task_id=%s error_type=%s", task.pk, task.error_code)
            task.attempts += 1
            task.save(update_fields=["name", "attempts", "completed_at", "next_attempt_at", "error_code", "updated_at"])
    return {"completed": completed, "failed": failed}
