from django.conf import settings
from django.db import models
from django.db.models import F, Q
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import ServiceOrder


class ReviewDirection(models.TextChoices):
    EMPLOYER_TO_WORKER = "EMPLOYER_TO_WORKER", "Employer to Worker"
    WORKER_TO_EMPLOYER = "WORKER_TO_EMPLOYER", "Worker to Employer"


class Review(TimeStampedUUIDModel):
    """Bidirectional review tied strictly to a COMPLETED ServiceOrder."""

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_reviews",
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews",
    )
    direction = models.CharField(
        max_length=30,
        choices=ReviewDirection.choices,
        db_index=True,
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "reviews_review"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "reviewer", "reviewee"],
                name="uq_review_order_participants",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="chk_review_rating_1_to_5",
            ),
            models.CheckConstraint(
                condition=~Q(reviewer=F("reviewee")),
                name="chk_review_no_self_review",
            ),
        ]
        indexes = [
            models.Index(fields=["reviewee", "direction"], name="idx_review_reviewee_dir"),
        ]

    def __str__(self):
        return f"Review({self.direction}: {self.rating}/5 for order {self.order_id})"
