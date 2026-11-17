from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.accounts.services.hiring_locks import lock_hiring_accounts
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.common.exceptions import BusinessRuleViolation, ConflictError, ForbiddenActionError
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.notifications.models import NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import OrderStatus, ServiceOrder
from apps.orders.services import OrderService
from apps.profiles.models import EmployerProfile, VerificationStatus, WorkerProfile


class InvitationService:
    """Transactional direct invitation workflow with deterministic lock ordering."""

    @classmethod
    @transaction.atomic
    def send_invitation(
        cls,
        employer: EmployerProfile,
        order_id,
        worker_id,
        message: str = "",
        proposed_budget=None,
        expires_in_days: int = 7,
    ) -> OrderInvitation:
        order = (
            ServiceOrder.objects.select_for_update(of=("self",))
            .select_related("employer__user")
            .filter(id=order_id)
            .first()
        )
        if not order:
            raise BusinessRuleViolation("Service order not found.", code="order_not_found", status_code=404)

        if str(order.employer_id) != str(employer.id):
            raise ForbiddenActionError("You can only send invitations for your own orders.")

        if order.status != OrderStatus.PUBLISHED or order.hired_worker_count >= order.capacity:
            raise BusinessRuleViolation(
                "Invitations can only be sent for PUBLISHED orders without an assigned worker.",
                code="order_not_open",
            )

        worker = (
            WorkerProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .filter(id=worker_id)
            .first()
        )
        if not worker or not worker.user.is_active or worker.user.account_status != "ACTIVE" or worker.user.is_anonymized:
            raise BusinessRuleViolation("Target worker not found or inactive.", code="worker_not_found", status_code=404)

        if str(worker.user_id) == str(employer.user_id):
            raise BusinessRuleViolation("You cannot invite yourself.", code="cannot_invite_self")

        # Batch 16 (PDR-PRODUCT-14 / Option A): KYC verification is optional.
        # Direct invitations may be sent to any active worker profile.

        if OrderInvitation.objects.filter(
            order=order,
            worker=worker,
            status__in=[InvitationStatus.PENDING, InvitationStatus.ACCEPTED],
        ).exists():
            raise ConflictError(
                "An active invitation already exists for this worker on this order.",
                code="duplicate_active_invitation",
            )

        try:
            invitation = OrderInvitation.objects.create(
                order=order,
                employer=employer,
                worker=worker,
                message=message,
                proposed_budget=proposed_budget,
                status=InvitationStatus.PENDING,
                expires_at=timezone.now() + timedelta(days=expires_in_days),
            )
        except IntegrityError as exc:
            raise ConflictError("Duplicate active invitation detected.", code="duplicate_active_invitation") from exc

        NotificationService.notify(
            recipient=worker.user,
            event_type=NotificationEventType.NEW_INVITATION,
            title=f"Direct Invitation: '{order.title}'",
            message=f"You have been invited to work on '{order.title}'.",
            data={"order_id": str(order.id), "invitation_id": str(invitation.id)},
        )
        return invitation

    @classmethod
    def accept_invitation(cls, invitation_id, worker: WorkerProfile) -> OrderInvitation:
        ref = OrderInvitation.objects.filter(id=invitation_id).values("order_id", "worker_id").first()
        if not ref:
            raise BusinessRuleViolation("Invitation not found.", code="invitation_not_found", status_code=404)

        expired_flag = False
        with transaction.atomic():
            lock_hiring_accounts(ref["order_id"], ref["worker_id"])
            # Level 1 lock: parent ServiceOrder
            order = (
                ServiceOrder.objects.select_for_update(of=("self",))
                .select_related("employer__user")
                .get(pk=ref["order_id"])
            )
            # Level 2 lock: WorkerProfile
            locked_worker = (
                WorkerProfile.objects.select_for_update(of=("self",))
                .select_related("user")
                .get(pk=worker.pk)
            )
            # Level 3 lock: OrderInvitation
            invitation = OrderInvitation.objects.select_for_update().get(pk=invitation_id)

            if str(invitation.worker_id) != str(locked_worker.id):
                raise ForbiddenActionError("You can only accept invitations addressed to you.")

            if invitation.status != InvitationStatus.PENDING:
                raise BusinessRuleViolation(
                    f"Invitation cannot be accepted in status '{invitation.status}'.",
                    code="invalid_invitation_transition",
                )

            now = timezone.now()
            if now > invitation.expires_at:
                invitation.status = InvitationStatus.EXPIRED
                invitation.responded_at = now
                invitation.save(update_fields=["status", "responded_at", "updated_at"])
                expired_flag = True
            else:
                # Batch 16 (PDR-PRODUCT-14 / Option A): KYC verification is optional.
                # Active, non-anonymized status is required to accept invitations.
                if not (locked_worker.user.is_active and not getattr(locked_worker.user, "is_anonymized", False)):
                    raise ForbiddenActionError("Active, non-anonymized worker account is required to accept invitations.", code="worker_not_active")

                if order.status != OrderStatus.PUBLISHED or order.hired_worker_count >= order.capacity:
                    raise ConflictError(
                        "This order is no longer open or already has an assigned worker.",
                        code="order_already_assigned",
                    )

                invitation.status = InvitationStatus.ACCEPTED
                invitation.responded_at = now
                invitation.save(update_fields=["status", "responded_at", "updated_at"])

                OrderService.assign_worker_locked(order, locked_worker)

                # Cancel competing pending invitations & reject pending applications on this order
                # An existing application can be accepted; an invitation never creates
                # an application or grants chat access by itself.
                OrderApplication.objects.filter(order=order, worker=locked_worker, status=ApplicationStatus.PENDING).update(
                    status=ApplicationStatus.ACCEPTED, responded_at=now, updated_at=now,
                )
                if order.status == OrderStatus.IN_PROGRESS:
                    OrderInvitation.objects.filter(order=order, status=InvitationStatus.PENDING).exclude(
                        pk=invitation.pk
                    ).update(status=InvitationStatus.CANCELLED, responded_at=now, updated_at=now)
                    OrderApplication.objects.filter(order=order, status=ApplicationStatus.PENDING).update(
                        status=ApplicationStatus.REJECTED, rejection_reason="Order capacity is full.",
                        responded_at=now, updated_at=now,
                    )

                NotificationService.notify(
                    recipient=order.employer.user,
                    event_type=NotificationEventType.INVITATION_ACCEPTED,
                    title=f"Invitation Accepted: '{order.title}'",
                    message=f"{locked_worker.full_name} accepted your invitation for '{order.title}'.",
                    data={"order_id": str(order.id), "invitation_id": str(invitation.id)},
                )

        if expired_flag:
            raise BusinessRuleViolation("This invitation has expired.", code="invitation_expired")

        return invitation

    @classmethod
    @transaction.atomic
    def reject_invitation(cls, invitation_id, worker: WorkerProfile) -> OrderInvitation:
        ref = OrderInvitation.objects.filter(id=invitation_id).values("order_id").first()
        if not ref:
            raise BusinessRuleViolation("Invitation not found.", code="invitation_not_found", status_code=404)

        order = ServiceOrder.objects.select_for_update(of=("self",)).select_related("employer__user").get(pk=ref["order_id"])
        invitation = OrderInvitation.objects.select_for_update().get(pk=invitation_id)

        if str(invitation.worker_id) != str(worker.id):
            raise ForbiddenActionError("You can only reject invitations addressed to you.")

        if invitation.status != InvitationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Invitation cannot be rejected in status '{invitation.status}'.",
                code="invalid_invitation_transition",
            )

        invitation.status = InvitationStatus.REJECTED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at", "updated_at"])

        NotificationService.notify(
            recipient=order.employer.user,
            event_type=NotificationEventType.INVITATION_REJECTED,
            title=f"Invitation Rejected: '{order.title}'",
            message=f"{worker.full_name} declined your invitation for '{order.title}'.",
            data={"order_id": str(order.id), "invitation_id": str(invitation.id)},
        )
        return invitation

    @classmethod
    @transaction.atomic
    def cancel_invitation(cls, invitation_id, employer: EmployerProfile) -> OrderInvitation:
        ref = OrderInvitation.objects.filter(id=invitation_id).values("order_id").first()
        if not ref:
            raise BusinessRuleViolation("Invitation not found.", code="invitation_not_found", status_code=404)

        ServiceOrder.objects.select_for_update().get(pk=ref["order_id"])
        invitation = OrderInvitation.objects.select_for_update().get(pk=invitation_id)

        if str(invitation.employer_id) != str(employer.id):
            raise ForbiddenActionError("You can only cancel invitations you sent.")

        if invitation.status != InvitationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Only PENDING invitations can be cancelled (current status: '{invitation.status}').",
                code="invalid_invitation_transition",
            )

        invitation.status = InvitationStatus.CANCELLED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at", "updated_at"])
        return invitation
