from django.db import transaction
from django.db.models import F
from django.utils import timezone
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.categories.models import Category
from apps.common.exceptions import BusinessRuleViolation, ConflictError, ForbiddenActionError
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.notifications.models import NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import OrderStatus, PaymentStatus, ServiceOrder
from apps.profiles.models import EmployerProfile, WorkerProfile


class OrderService:
    """Transactional state machine and ownership enforcement for ServiceOrders."""

    EDITABLE_STATUSES = {OrderStatus.DRAFT, OrderStatus.PUBLISHED, OrderStatus.PAUSED}
    TERMINAL_STATUSES = {OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.CLOSED}

    @classmethod
    def assign_worker_locked(cls, order, worker):
        """Caller holds the parent order lock inside atomic; SQLite uses IMMEDIATE writes."""
        if order.status != OrderStatus.PUBLISHED:
            raise ConflictError("Order is not accepting workers.", code="order_already_assigned")
        hired = order.get_hired_workers()
        if any(w.pk == worker.pk for w in hired):
            raise ConflictError("Worker is already hired for this order.", code="worker_already_assigned")
        if len(hired) >= order.capacity:
            raise ConflictError("Order capacity is full.", code="order_already_assigned")
        if not worker.user.is_active or worker.user.is_anonymized or worker.user.account_status != "ACTIVE":
            raise ForbiddenActionError("Worker account is not active.", code="worker_not_active")
        if not worker.is_available:
            raise ConflictError("Worker is not currently available for hiring.", code="worker_unavailable")
        if order.assigned_worker_id:
            order.assigned_workers.add(order.assigned_worker)
        else:
            order.assigned_worker = worker  # Keep the original single-worker API compatible.
        order.assigned_workers.add(worker)
        order.status = OrderStatus.IN_PROGRESS if len(hired) + 1 >= order.capacity else OrderStatus.PUBLISHED
        order.save(update_fields=["assigned_worker", "status", "updated_at"])

    @classmethod
    @transaction.atomic
    def create_order(cls, employer: EmployerProfile, validated_data: dict) -> ServiceOrder:
        category = validated_data["category"]
        if not category.is_active:
            raise BusinessRuleViolation("Cannot create an order under an inactive category.", code="inactive_category")

        initial_status = validated_data.pop("status", OrderStatus.DRAFT)
        if initial_status not in (OrderStatus.DRAFT, OrderStatus.PUBLISHED):
            raise BusinessRuleViolation(
                "New orders can only start in DRAFT or PUBLISHED status.",
                code="invalid_initial_status",
            )

        now = timezone.now()
        order = ServiceOrder.objects.create(
            employer=employer,
            status=initial_status,
            payment_status=PaymentStatus.DISABLED,
            published_at=now if initial_status == OrderStatus.PUBLISHED else None,
            **validated_data,
        )
        EmployerProfile.objects.filter(pk=employer.pk).update(posted_orders_count=F("posted_orders_count") + 1)
        return order

    @classmethod
    def _get_owned_order_locked(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = (
            ServiceOrder.objects.select_for_update(of=("self",))
            .select_related("employer", "assigned_worker")
            .filter(id=order_id)
            .first()
        )
        if not order:
            raise BusinessRuleViolation("Service order not found.", code="order_not_found", status_code=404)
        if str(order.employer_id) != str(employer.id):
            raise ForbiddenActionError("You can only manage your own service orders.")
        return order

    @classmethod
    @transaction.atomic
    def update_order(cls, order_id, employer: EmployerProfile, validated_data: dict) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status not in cls.EDITABLE_STATUSES:
            raise BusinessRuleViolation(
                f"Orders in status '{order.status}' cannot be edited.",
                code="order_not_editable",
            )
        if "category" in validated_data and not validated_data["category"].is_active:
            raise BusinessRuleViolation("Selected category is inactive.", code="inactive_category")
        if validated_data.get("capacity", order.capacity) < order.hired_worker_count:
            raise BusinessRuleViolation("Capacity cannot be less than the hired team.", code="capacity_below_hired")

        for field, value in validated_data.items():
            setattr(order, field, value)
        order.save()
        return order

    @classmethod
    @transaction.atomic
    def delete_order(cls, order_id, employer: EmployerProfile) -> None:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status != OrderStatus.DRAFT:
            raise BusinessRuleViolation(
                "Only DRAFT orders can be permanently deleted. Use cancel or close for published/active orders.",
                code="cannot_delete_non_draft",
            )
        order.delete()

    @classmethod
    @transaction.atomic
    def publish_order(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status not in (OrderStatus.DRAFT, OrderStatus.PAUSED):
            raise BusinessRuleViolation(
                f"Cannot publish order from status '{order.status}'.",
                code="invalid_status_transition",
            )
        if not order.category.is_active:
            raise BusinessRuleViolation("Cannot publish an order whose category is inactive.", code="inactive_category")

        order.status = OrderStatus.PUBLISHED
        if not order.published_at:
            order.published_at = timezone.now()
        order.save(update_fields=["status", "published_at", "updated_at"])
        return order

    @classmethod
    @transaction.atomic
    def pause_order(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status != OrderStatus.PUBLISHED:
            raise BusinessRuleViolation("Only PUBLISHED orders can be paused.", code="invalid_status_transition")
        order.status = OrderStatus.PAUSED
        order.save(update_fields=["status", "updated_at"])
        return order

    @classmethod
    @transaction.atomic
    def _reject_pending_requests(cls, order: ServiceOrder, reason: str, new_status: str) -> None:
        now = timezone.now()
        pending_apps = list(
            OrderApplication.objects.select_for_update(of=("self",))
            .select_related("worker__user")
            .filter(order=order, status=ApplicationStatus.PENDING)
        )
        for app in pending_apps:
            app.status = ApplicationStatus.REJECTED
            app.rejection_reason = reason
            app.responded_at = now
            app.save(update_fields=["status", "rejection_reason", "responded_at", "updated_at"])
            NotificationService.notify(
                recipient=app.worker.user,
                event_type=NotificationEventType.ORDER_STATUS_CHANGED,
                title=f"Order '{order.title}' {new_status.lower()}",
                message=f"The order '{order.title}' was marked {new_status}. Your pending application was closed.",
                data={"order_id": str(order.id), "status": new_status},
            )

        pending_invs = list(
            OrderInvitation.objects.select_for_update(of=("self",))
            .select_related("worker__user")
            .filter(order=order, status=InvitationStatus.PENDING)
        )
        for inv in pending_invs:
            inv.status = InvitationStatus.CANCELLED
            inv.responded_at = now
            inv.save(update_fields=["status", "responded_at", "updated_at"])
            NotificationService.notify(
                recipient=inv.worker.user,
                event_type=NotificationEventType.ORDER_STATUS_CHANGED,
                title=f"Order '{order.title}' {new_status.lower()}",
                message=f"The order '{order.title}' was marked {new_status}. Your pending invitation was cancelled.",
                data={"order_id": str(order.id), "status": new_status},
            )

    @classmethod
    @transaction.atomic
    def cancel_order(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status in cls.TERMINAL_STATUSES:
            raise BusinessRuleViolation(
                f"Order is already in terminal status '{order.status}'.",
                code="invalid_status_transition",
            )
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        cls._reject_pending_requests(order, "Order was cancelled by employer.", OrderStatus.CANCELLED)

        if order.assigned_worker:
            NotificationService.notify(
                recipient=order.assigned_worker.user,
                event_type=NotificationEventType.ORDER_STATUS_CHANGED,
                title=f"Order Cancelled: {order.title}",
                message=f"Employer cancelled order '{order.title}'.",
                data={"order_id": str(order.id), "status": OrderStatus.CANCELLED},
            )
        return order

    @classmethod
    @transaction.atomic
    def close_order(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.CLOSED):
            raise BusinessRuleViolation(
                f"Order is already in terminal status '{order.status}'.",
                code="invalid_status_transition",
            )
        order.status = OrderStatus.CLOSED
        order.save(update_fields=["status", "updated_at"])
        cls._reject_pending_requests(order, "Order was closed by employer.", OrderStatus.CLOSED)
        return order

    @classmethod
    @transaction.atomic
    def complete_order(cls, order_id, employer: EmployerProfile) -> ServiceOrder:
        order = cls._get_owned_order_locked(order_id, employer)
        if order.status not in (OrderStatus.IN_PROGRESS, OrderStatus.PUBLISHED, OrderStatus.PAUSED):
            raise BusinessRuleViolation(
                "Only IN_PROGRESS orders with an assigned worker can be completed.",
                code="invalid_status_transition",
            )
        workers = order.get_hired_workers()
        if not workers:
            raise BusinessRuleViolation("Order has no assigned worker.", code="no_assigned_worker")

        now = timezone.now()
        order.status = OrderStatus.COMPLETED
        order.completed_at = now
        order.save(update_fields=["status", "completed_at", "updated_at"])
        cls._reject_pending_requests(order, "Order completed.", OrderStatus.COMPLETED)

        EmployerProfile.objects.filter(pk=order.employer_id).update(
            completed_orders_count=F("completed_orders_count") + 1
        )
        WorkerProfile.objects.filter(pk__in=[worker.pk for worker in workers]).update(
            completed_orders_count=F("completed_orders_count") + 1
        )

        for worker in workers:
            NotificationService.notify(
                recipient=worker.user,
                event_type=NotificationEventType.ORDER_STATUS_CHANGED,
                title=f"Order Completed: {order.title}",
                message=f"Employer marked '{order.title}' as COMPLETED. You can now leave a review.",
                data={"order_id": str(order.id), "status": OrderStatus.COMPLETED},
            )
        return order
