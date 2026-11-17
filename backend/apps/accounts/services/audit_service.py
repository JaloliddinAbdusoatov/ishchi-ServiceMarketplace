"""Transactional administrative audit using Django's existing log table.

Only fixed action names and identifiers are stored; never copy request payloads,
phone numbers, free-text notes, or credentials into the audit trail.
"""
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import connection


def record_admin_action(actor, action, target):
    if not connection.in_atomic_block:
        raise RuntimeError("Administrative audit requires the mutation transaction.")
    return LogEntry.objects.create(
        user=actor,
        content_type=ContentType.objects.get_for_model(target),
        object_id=str(target.pk),
        object_repr=f"{target._meta.label}:{target.pk}",
        action_flag=CHANGE,
        change_message=action,
    )
