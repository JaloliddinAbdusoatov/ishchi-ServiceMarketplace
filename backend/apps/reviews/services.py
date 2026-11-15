from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from apps.common.exceptions import BusinessRuleViolation, ConflictError, ForbiddenActionError
from apps.notifications.models import NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import OrderStatus, ServiceOrder
from apps.profiles.models import EmployerProfile, WorkerProfile
from apps.reviews.models import Review, ReviewDirection


class ReviewService:
    """Enforces completed-order bidirectional review integrity and updates profile rating aggregates."""

    @classmethod
    def participants(cls, order, reviewer, reviewee_id=None):
        if order.status != OrderStatus.COMPLETED:
            raise BusinessRuleViolation("Reviews can only be submitted for COMPLETED orders.", code="order_not_completed")
        workers = order.get_hired_workers()
        if not workers:
            raise BusinessRuleViolation("Order has no assigned worker.", code="no_assigned_worker")
        if str(order.employer.user_id) == str(reviewer.id):
            targets = [w.user for w in workers if not reviewee_id or str(w.user_id) == str(reviewee_id)]
            if not targets:
                raise ForbiddenActionError("Review target must be a hired worker.")
            reviewee = next((u for u in targets if not Review.objects.filter(order=order, reviewer=reviewer, reviewee=u).exists()), targets[0])
            direction = ReviewDirection.EMPLOYER_TO_WORKER
        elif any(str(w.user_id) == str(reviewer.id) for w in workers):
            direction, reviewee = ReviewDirection.WORKER_TO_EMPLOYER, order.employer.user
            if reviewee_id and str(reviewee_id) != str(reviewee.id):
                raise ForbiddenActionError("Workers can only review this order's employer.")
        else:
            raise ForbiddenActionError("Only the employer and hired workers can review this order.")
        if str(reviewee.id) == str(reviewer.id):
            raise BusinessRuleViolation("Users cannot review themselves.", code="self_review_forbidden")
        return direction, reviewee

    @classmethod
    @transaction.atomic
    def create_review(cls, reviewer, order_id, rating: int, comment: str = "", reviewee_id=None) -> Review:
        order = (
            ServiceOrder.objects.select_for_update(of=("self",))
            .select_related("employer__user", "assigned_worker__user")
            .filter(id=order_id)
            .first()
        )
        if not order:
            raise BusinessRuleViolation("Service order not found.", code="order_not_found", status_code=404)

        direction, reviewee = cls.participants(order, reviewer, reviewee_id)
        if not 1 <= rating <= 5:
            raise BusinessRuleViolation("Rating must be between 1 and 5.", code="invalid_rating")
        if Review.objects.filter(order=order, reviewer=reviewer, reviewee=reviewee).exists():
            raise ConflictError(
                "A review for this order and direction already exists.",
                code="duplicate_review",
            )

        try:
            review = Review.objects.create(
                order=order,
                reviewer=reviewer,
                reviewee=reviewee,
                direction=direction,
                rating=rating,
                comment=comment,
            )
        except IntegrityError as exc:
            raise ConflictError("Duplicate review detected.", code="duplicate_review") from exc

        # Recalculate reviewee's rating aggregate atomically
        agg = Review.objects.filter(reviewee=reviewee, direction=direction).aggregate(
            avg=Avg("rating"),
            cnt=Count("id"),
        )
        avg_val = Decimal(str(round(agg["avg"] or 0, 2)))
        cnt_val = agg["cnt"] or 0

        if direction == ReviewDirection.EMPLOYER_TO_WORKER:
            WorkerProfile.objects.filter(user=reviewee).update(rating_avg=avg_val, review_count=cnt_val)
        else:
            EmployerProfile.objects.filter(user=reviewee).update(rating_avg=avg_val, review_count=cnt_val)

        NotificationService.notify(
            recipient=reviewee,
            event_type=NotificationEventType.NEW_REVIEW,
            title=f"New {rating}-star review received",
            message=f"You received a {rating}/5 review for '{order.title}'.",
            data={"order_id": str(order.id), "review_id": str(review.id), "rating": rating},
        )
        return review
