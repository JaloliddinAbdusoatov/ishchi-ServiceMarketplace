from rest_framework import serializers
from apps.applications.models import OrderApplication


class OrderApplicationSerializer(serializers.ModelSerializer):
    order_title = serializers.CharField(source="order.title", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True)
    worker_rating = serializers.DecimalField(source="worker.rating_avg", max_digits=3, decimal_places=2, read_only=True)
    worker_is_verified = serializers.BooleanField(source="worker.is_verified", read_only=True)

    class Meta:
        model = OrderApplication
        fields = [
            "id",
            "order",
            "order_title",
            "order_status",
            "worker",
            "worker_name",
            "worker_rating",
            "worker_is_verified",
            "cover_message",
            "proposed_price",
            "status",
            "rejection_reason",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderApplicationCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
    cover_message = serializers.CharField(min_length=5, max_length=2000)
    proposed_price = serializers.DecimalField(max_digits=14, decimal_places=2)

    def validate_proposed_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Proposed price must be strictly greater than zero.")
        return value


class ApplicationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
