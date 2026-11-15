from rest_framework import serializers
from apps.accounts.models import User
from apps.chat.models import Message
from apps.orders.models import ServiceOrder
from apps.reports.models import Report, ReportReason, ReportStatus, ReportTargetType


class ReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.full_name", read_only=True, default=None)

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "reporter_name",
            "target_type",
            "target_user",
            "target_order",
            "target_message",
            "reason",
            "description",
            "status",
            "admin_resolution",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=ReportTargetType.choices)
    target_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=ReportReason.choices)
    description = serializers.CharField(min_length=5, max_length=2000)


class ReportResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ReportStatus.UNDER_REVIEW, ReportStatus.RESOLVED, ReportStatus.REJECTED]
    )
    admin_resolution = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
