from django.db import transaction
from django.utils import timezone
from apps.accounts.models import AccountStatus
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.chat.models import Conversation, Message
from apps.common.exceptions import BusinessRuleViolation, ForbiddenActionError
from apps.notifications.models import NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile


class ChatService:
    """Server-side authorized order-scoped chat system."""

    @classmethod
    def _verify_worker_order_participation(cls, order: ServiceOrder, worker: WorkerProfile) -> None:
        has_valid_app = OrderApplication.objects.filter(
            order=order,
            worker=worker,
            status__in=[ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED],
        ).exists()
        if not has_valid_app or not worker.user.is_active or worker.user.is_anonymized or worker.user.account_status != AccountStatus.ACTIVE:
            raise ForbiddenActionError(
                "Only a worker who has submitted an application to this order may access its chat.",
                code="chat_application_required",
            )
        employer = order.employer.user
        if not employer.is_active or employer.is_anonymized or employer.account_status != AccountStatus.ACTIVE:
            raise ForbiddenActionError("Employer account is not active.", code="chat_participant_inactive")

    @classmethod
    def assert_conversation_access(cls, conversation: Conversation, user) -> None:
        is_employer = str(conversation.employer.user_id) == str(user.id)
        is_worker = str(conversation.worker.user_id) == str(user.id)
        if not (is_employer or is_worker):
            raise ForbiddenActionError("You are not a participant of this conversation.", code="chat_access_denied")
        cls._verify_worker_order_participation(conversation.order, conversation.worker)

    @classmethod
    @transaction.atomic
    def get_or_create_conversation(cls, user, order_id, worker_id=None) -> tuple[Conversation, bool]:
        order = (
            ServiceOrder.objects.select_related("employer__user", "assigned_worker__user")
            .filter(id=order_id)
            .first()
        )
        if not order:
            raise BusinessRuleViolation("Service order not found.", code="order_not_found", status_code=404)

        is_employer = str(order.employer.user_id) == str(user.id)
        if is_employer:
            target_worker_id = worker_id or order.assigned_worker_id
            if not target_worker_id:
                raise BusinessRuleViolation(
                    "worker_id is required when employer starts a conversation on an unassigned order.",
                    code="worker_id_required",
                )
            worker = WorkerProfile.objects.select_related("user").filter(id=target_worker_id).first()
            if not worker:
                raise BusinessRuleViolation("Worker not found.", code="worker_not_found", status_code=404)
            cls._verify_worker_order_participation(order, worker)
        elif hasattr(user, "worker_profile"):
            worker = user.worker_profile
            cls._verify_worker_order_participation(order, worker)
        else:
            raise ForbiddenActionError("You do not have permission to start a chat for this order.")

        conv, created = Conversation.objects.get_or_create(
            order=order,
            worker=worker,
            defaults={"employer": order.employer},
        )
        return conv, created

    @classmethod
    @transaction.atomic
    def send_message(cls, conversation: Conversation, sender, content: str = "", attachment=None) -> Message:
        cls.assert_conversation_access(conversation, sender)
        clean_content = (content or "").strip()
        if not clean_content and not attachment:
            raise BusinessRuleViolation("Message must contain text content or an attachment.", code="empty_message")

        msg = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=clean_content,
            attachment=attachment,
        )
        conversation.last_message_at = msg.created_at
        conversation.save(update_fields=["last_message_at", "updated_at"])

        recipient = (
            conversation.worker.user
            if str(sender.id) == str(conversation.employer.user_id)
            else conversation.employer.user
        )
        NotificationService.notify(
            recipient=recipient,
            event_type=NotificationEventType.NEW_MESSAGE,
            title=f"New message on '{conversation.order.title}'",
            message=clean_content[:120] if clean_content else "Sent an attachment.",
            data={"conversation_id": str(conversation.id), "order_id": str(conversation.order_id), "message_id": str(msg.id)},
        )
        return msg

    @classmethod
    @transaction.atomic
    def mark_conversation_read(cls, conversation: Conversation, reader) -> int:
        cls.assert_conversation_access(conversation, reader)
        now = timezone.now()
        return (
            Message.objects.filter(conversation=conversation, is_read=False)
            .exclude(sender=reader)
            .update(is_read=True, read_at=now, updated_at=now)
        )
