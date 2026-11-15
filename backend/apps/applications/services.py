from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.common.exceptions import BusinessRuleViolation, ConflictError, ForbiddenActionError
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.notifications.models import NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import OrderStatus, ServiceOrder
from apps.orders.services import OrderService
from apps.profiles.models import EmployerProfile, VerificationStatus, WorkerProfile


class ApplicationService:
    """Transactional worker application workflow with strict lock ordering."""

    @classmethod
    @transaction.atomic
    def submit_application(
        cls,
        worker: WorkerProfile,
        order_id,
        cover_message: str,
        proposed_price,
    ) -> OrderApplication:
        order = (
            ServiceOrder.objects.select_for_update(of=("self",))
            .select_related("employer__user")
            .filter(id=order_id)
            .first()
        )
        if not order:
            raise BusinessRuleViolation("Service order not found.", code="order_not_found", status_code=404)

        locked_worker = (
            WorkerProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(pk=worker.pk)
        )

        # Batch 16 (PDR-PRODUCT-14 / Option A): KYC verification is optional.
        # Active, non-anonymized worker profile is required for marketplace applications.
        if not (locked_worker.user.is_active and locked_worker.user.account_status == "ACTIVE" and not getattr(locked_worker.user, "is_anonymized", False)):
            raise ForbiddenActionError(
                "Active, non-anonymized worker account is required to submit applications.",
                code="worker_not_active",
            )

        if str(order.employer.user_id) == str(locked_worker.user_id):
            raise BusinessRuleViolation(
                "You cannot apply to your own service order.",
                code="cannot_apply_own_order",
            )

        if order.status != OrderStatus.PUBLISHED or order.hired_worker_count >= order.capacity:
            raise BusinessRuleViolation(
                "Applications can only be submitted to PUBLISHED orders without an assigned worker.",
                code="order_not_accepting_applications",
            )

        if any(w.pk == locked_worker.pk for w in order.get_hired_workers()):
            raise ConflictError("You are already hired for this order.", code="worker_already_assigned")
        if OrderApplication.objects.filter(
            order=order,
            worker=locked_worker,
            status__in=[ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED],
        ).exists():
            raise ConflictError(
                "You already have an active application for this order.",
                code="duplicate_active_application",
            )

        try:
            application = OrderApplication.objects.create(
                order=order,
                worker=locked_worker,
                cover_message=cover_message,
                proposed_price=proposed_price,
                status=ApplicationStatus.PENDING,
            )
        except IntegrityError as exc:
            raise ConflictError(
                "Duplicate active application detected.",
                code="duplicate_active_application",
            ) from exc

        NotificationService.notify(
            recipient=order.employer.user,
            event_type=NotificationEventType.NEW_APPLICATION,
            title=f"New application on '{order.title}'",
            message=f"{locked_worker.full_name} applied with a proposed price of {proposed_price}.",
            data={"order_id": str(order.id), "application_id": str(application.id)},
        )
        return application

    @classmethod
    @transaction.atomic
    def withdraw_application(cls, application_id, worker: WorkerProfile) -> OrderApplication:
        ref = OrderApplication.objects.filter(id=application_id).values("order_id").first()
        if not ref:
            raise BusinessRuleViolation("Application not found.", code="application_not_found", status_code=404)

        ServiceOrder.objects.select_for_update().get(pk=ref["order_id"])
        application = OrderApplication.objects.select_for_update(of=("self",)).select_related("order").get(pk=application_id)

        if str(application.worker_id) != str(worker.id):
            raise ForbiddenActionError("You can only withdraw your own applications.")

        if application.status != ApplicationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Cannot withdraw application in status '{application.status}'.",
                code="invalid_application_transition",
            )

        application.status = ApplicationStatus.WITHDRAWN
        application.responded_at = timezone.now()
        application.save(update_fields=["status", "responded_at", "updated_at"])
        return application

    @classmethod
    @transaction.atomic
    def accept_application(cls, application_id, employer: EmployerProfile) -> OrderApplication:
        ref = OrderApplication.objects.filter(id=application_id).values("order_id", "worker_id").first()
        if not ref:
            raise BusinessRuleViolation("Application not found.", code="application_not_found", status_code=404)

        # Level 1 lock: parent ServiceOrder
        order = (
            ServiceOrder.objects.select_for_update(of=("self",))
            .select_related("employer__user")
            .get(pk=ref["order_id"])
        )
        if str(order.employer_id) != str(employer.id):
            raise ForbiddenActionError("Only the order's employer can accept applications.")

        # Level 2 lock: WorkerProfile
        worker = (
            WorkerProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(pk=ref["worker_id"])
        )

        # Level 3 lock: OrderApplication
        application = OrderApplication.objects.select_for_update().get(pk=application_id)

        if application.status != ApplicationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Only PENDING applications can be accepted (current status: '{application.status}').",
                code="invalid_application_transition",
            )

        if order.status != OrderStatus.PUBLISHED or order.hired_worker_count >= order.capacity:
            raise ConflictError(
                "This order is no longer open or already has an assigned worker.",
                code="order_already_assigned",
            )

        # Batch 16 (PDR-PRODUCT-14 / Option A): KYC verification is optional.
        # Verified badge is informational only; active status is required for hiring.
        if not (worker.user.is_active and not getattr(worker.user, "is_anonymized", False)):
            raise BusinessRuleViolation(
                "Applicant worker account is no longer active.",
                code="worker_not_eligible",
            )

        now = timezone.now()
        application.status = ApplicationStatus.ACCEPTED
        application.responded_at = now
        application.save(update_fields=["status", "responded_at", "updated_at"])

        OrderService.assign_worker_locked(order, worker)

        # Reject other competing pending applications
        other_apps = list(
            OrderApplication.objects.select_for_update(of=("self",))
            .select_related("worker__user")
            .filter(order=order, status=ApplicationStatus.PENDING)
            .exclude(pk=application.pk)
        )
        if order.status != OrderStatus.IN_PROGRESS:
            other_apps = []  # Remaining slots can still receive applications.
        for other in other_apps:
            other.status = ApplicationStatus.REJECTED
            other.rejection_reason = "Another applicant was selected for this order."
            other.responded_at = now
            other.save(update_fields=["status", "rejection_reason", "responded_at", "updated_at"])
            NotificationService.notify(
                recipient=other.worker.user,
                event_type=NotificationEventType.APPLICATION_REJECTED,
                title=f"Application not selected for '{order.title}'",
                message=f"Another worker was selected for '{order.title}'.",
                data={"order_id": str(order.id), "application_id": str(other.id)},
            )

        # Cancel any pending invitations on this order
        if order.status == OrderStatus.IN_PROGRESS:
            OrderInvitation.objects.filter(order=order, status=InvitationStatus.PENDING).update(
                status=InvitationStatus.CANCELLED, responded_at=now, updated_at=now,
            )

        NotificationService.notify(
            recipient=worker.user,
            event_type=NotificationEventType.APPLICATION_ACCEPTED,
            title=f"Application Accepted: '{order.title}'",
            message=f"Your application for '{order.title}' was accepted! You are now hired.",
            data={"order_id": str(order.id), "application_id": str(application.id)},
        )
        return application

    @classmethod
    @transaction.atomic
    def reject_application(cls, application_id, employer: EmployerProfile, reason: str = "") -> OrderApplication:
        ref = OrderApplication.objects.filter(id=application_id).values("order_id").first()
        if not ref:
            raise BusinessRuleViolation("Application not found.", code="application_not_found", status_code=404)

        order = ServiceOrder.objects.select_for_update().get(pk=ref["order_id"])
        if str(order.employer_id) != str(employer.id):
            raise ForbiddenActionError("Only the order's employer can reject applications.")

        application = (
            OrderApplication.objects.select_for_update(of=("self",))
            .select_related("worker__user")
            .get(pk=application_id)
        )
        if application.status != ApplicationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Only PENDING applications can be rejected (current status: '{application.status}').",
                code="invalid_application_transition",
            )

        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = reason
        application.responded_at = timezone.now()
        application.save(update_fields=["status", "rejection_reason", "responded_at", "updated_at"])

        NotificationService.notify(
            recipient=application.worker.user,
            event_type=NotificationEventType.APPLICATION_REJECTED,
            title=f"Application Rejected: '{order.title}'",
            message=f"Your application for '{order.title}' was rejected.",
            data={"order_id": str(order.id), "application_id": str(application.id)},
        )
        return application
