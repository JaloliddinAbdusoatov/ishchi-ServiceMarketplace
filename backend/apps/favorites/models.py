from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import ServiceOrder
from apps.profiles.models import WorkerProfile


class FavoriteWorker(TimeStampedUUIDModel):
    """Saved favorite worker bookmark for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_workers",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        db_table = "favorites_worker"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "worker"],
                name="uq_favorite_user_worker",
            ),
        ]

    def __str__(self):
        return f"FavoriteWorker({self.user_id} -> {self.worker_id})"


class FavoriteOrder(TimeStampedUUIDModel):
    """Saved favorite service order bookmark for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_orders",
    )
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        db_table = "favorites_order"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "order"],
                name="uq_favorite_user_order",
            ),
        ]

    def __str__(self):
        return f"FavoriteOrder({self.user_id} -> {self.order_id})"
