from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsActiveAccount
from apps.chat.models import Message
from apps.chat.services import ChatService
from apps.orders.access import visible_orders
from apps.common.exceptions import BusinessRuleViolation
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.orders.models import ServiceOrder
from apps.reports.models import Report, ReportStatus, ReportTargetType
from apps.reports.serializers import ReportCreateSerializer, ReportSerializer


class ReportListCreateView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="List My Submitted Reports", responses={200: ReportSerializer(many=True)}, tags=["Reports"])
    def get(self, request):
        qs = Report.objects.filter(reporter=request.user).select_related("reporter", "resolved_by")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ReportSerializer(page, many=True).data)

    @extend_schema(
        summary="Submit Moderation Report",
        description="Report a user, service order, or chat message.",
        request=ReportCreateSerializer,
        responses={201: ReportSerializer},
        tags=["Reports"],
    )
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_type = serializer.validated_data["target_type"]
        target_id = serializer.validated_data["target_id"]

        kwargs = {
            "reporter": request.user,
            "target_type": target_type,
            "reason": serializer.validated_data["reason"],
            "description": serializer.validated_data["description"],
            "status": ReportStatus.PENDING,
        }
        if target_type == ReportTargetType.USER:
            target_user = get_object_or_404(User, id=target_id)
            if str(target_user.id) == str(request.user.id):
                raise BusinessRuleViolation("You cannot report yourself.", code="cannot_report_self")
            kwargs["target_user"] = target_user
        elif target_type == ReportTargetType.ORDER:
            target_order = get_object_or_404(visible_orders(request.user), id=target_id)
            kwargs["target_order"] = target_order
        elif target_type == ReportTargetType.MESSAGE:
            target_msg = get_object_or_404(Message, id=target_id)
            ChatService.assert_conversation_access(target_msg.conversation, request.user)
            kwargs["target_message"] = target_msg

        report = Report.objects.create(**kwargs)
        return success_response(
            data=ReportSerializer(report).data,
            message="Report submitted for administrator review.",
            status_code=status.HTTP_201_CREATED,
        )
