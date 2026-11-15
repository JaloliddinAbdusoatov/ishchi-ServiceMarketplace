from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from apps.accounts.permissions import IsActiveAccount
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService


class NotificationListView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="List Notifications",
        description="Lists authenticated user's notifications with read/unread filter and unread_count.",
        parameters=[
            OpenApiParameter(name="is_read", type=bool, required=False),
            OpenApiParameter(name="event_type", type=str, required=False),
        ],
        responses={200: NotificationSerializer(many=True)},
        tags=["Notifications"],
    )
    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        is_read_param = request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                qs = qs.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                qs = qs.filter(is_read=False)

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        resp = paginator.get_paginated_response(serializer.data)
        resp.data["unread_count"] = unread_count
        return resp


class NotificationMarkReadView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Mark Notification as Read",
        responses={200: NotificationSerializer},
        tags=["Notifications"],
    )
    def post(self, request, notification_id):
        notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        NotificationService.mark_read(notif)
        return success_response(data=NotificationSerializer(notif).data, message="Notification marked as read.")


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Mark All Notifications as Read",
        responses={200: OpenApiResponse(description="All notifications marked read")},
        tags=["Notifications"],
    )
    def post(self, request):
        updated = NotificationService.mark_all_read(request.user)
        return success_response(data={"marked_read_count": updated}, message="All notifications marked as read.")


class NotificationDeleteView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Delete Notification",
        responses={200: OpenApiResponse(description="Notification deleted")},
        tags=["Notifications"],
    )
    def delete(self, request, notification_id):
        notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notif.delete()
        return success_response(message="Notification deleted.", status_code=status.HTTP_200_OK)
