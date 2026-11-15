from rest_framework import serializers
from apps.invitations.models import OrderInvitation


class OrderInvitationSerializer(serializers.ModelSerializer):
    order_title = serializers.CharField(source="order.title", read_only=True)
    employer_name = serializers.CharField(source="employer.full_name", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True)

    class Meta:
        model = OrderInvitation
        fields = [
            "id",
            "order",
            "order_title",
            "employer",
            "employer_name",
            "worker",
            "worker_name",
            "message",
            "proposed_budget",
            "status",
            "expires_at",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderInvitationCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
    worker = serializers.UUIDField()
    message = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
    proposed_budget = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=60, required=False, default=7)

    def validate_proposed_budget(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Proposed budget must be greater than zero.")
        return value
