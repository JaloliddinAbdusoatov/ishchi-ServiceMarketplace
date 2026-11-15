from pathlib import Path
from django.http import FileResponse, Http404
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.accounts.permissions import IsActiveAccount
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.chat.services import ChatService
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response


class ConversationListCreateView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="List My Conversations", responses={200: ConversationSerializer(many=True)}, tags=["Chat"])
    def get(self, request):
        user = request.user
        q = Q()
        if hasattr(user, "employer_profile"):
            q |= Q(employer=user.employer_profile)
        if hasattr(user, "worker_profile"):
            q |= Q(worker=user.worker_profile)

        qs = (
            Conversation.objects.filter(q).select_related("order", "employer", "worker").distinct()
            if q
            else Conversation.objects.none()
        )
        # A withdrawn/rejected application must not expose cached message previews.
        valid_application = OrderApplication.objects.filter(
            order_id=OuterRef("order_id"), worker_id=OuterRef("worker_id"),
            status__in=[ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED],
        )
        qs = qs.filter(
            Exists(valid_application),
            worker__user__is_active=True, worker__user__is_anonymized=False,
            worker__user__account_status="ACTIVE",
            employer__user__is_active=True, employer__user__is_anonymized=False,
            employer__user__account_status="ACTIVE",
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ConversationSerializer(page, many=True, context={"request": request}).data
        )

    @extend_schema(
        summary="Open or Create Order Conversation",
        request=ConversationCreateSerializer,
        responses={200: ConversationSerializer, 201: ConversationSerializer},
        tags=["Chat"],
    )
    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv, created = ChatService.get_or_create_conversation(
            user=request.user,
            order_id=serializer.validated_data["order"],
            worker_id=serializer.validated_data.get("worker"),
        )
        return success_response(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Conversation created." if created else "Conversation retrieved.",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="Get Conversation Detail", responses={200: ConversationSerializer}, tags=["Chat"])
    def get(self, request, conversation_id):
        conv = get_object_or_404(Conversation.objects.select_related("order", "employer__user", "worker__user"), id=conversation_id)
        ChatService.assert_conversation_access(conv, request.user)
        return success_response(data=ConversationSerializer(conv, context={"request": request}).data)


class ConversationMessagesView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="List Conversation Messages (Supports Polling)",
        parameters=[
            OpenApiParameter(name="after", type=str, required=False, description="ISO-8601 timestamp for polling new messages"),
            OpenApiParameter(name="unread_only", type=bool, required=False),
        ],
        responses={200: MessageSerializer(many=True)},
        tags=["Chat"],
    )
    def get(self, request, conversation_id):
        conv = get_object_or_404(Conversation.objects.select_related("order", "employer__user", "worker__user"), id=conversation_id)
        ChatService.assert_conversation_access(conv, request.user)

        qs = conv.messages.select_related("sender").order_by("created_at")
        after_param = request.query_params.get("after")
        if after_param:
            dt = parse_datetime(after_param)
            if dt:
                qs = qs.filter(created_at__gt=dt)
        if request.query_params.get("unread_only", "").lower() in ("true", "1"):
            qs = qs.filter(is_read=False).exclude(sender=request.user)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(MessageSerializer(page, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Send Message in Conversation",
        request=MessageCreateSerializer,
        responses={201: MessageSerializer},
        tags=["Chat"],
    )
    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation.objects.select_related("order", "employer__user", "worker__user"), id=conversation_id)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = ChatService.send_message(
            conversation=conv,
            sender=request.user,
            content=serializer.validated_data.get("content", ""),
            attachment=serializer.validated_data.get("attachment"),
        )
        return success_response(
            data=MessageSerializer(msg, context={"request": request}).data,
            message="Message sent.",
            status_code=status.HTTP_201_CREATED,
        )


class ConversationMarkReadView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="Mark Conversation Messages as Read", tags=["Chat"])
    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation.objects.select_related("order", "employer__user", "worker__user"), id=conversation_id)
        updated = ChatService.mark_conversation_read(conv, request.user)
        return success_response(data={"marked_read_count": updated}, message="Messages marked as read.")


class MessageAttachmentView(APIView):
    permission_classes = [IsActiveAccount]

    def get(self, request, message_id):
        message = get_object_or_404(Message.objects.select_related(
            "conversation__order__employer__user", "conversation__worker__user", "conversation__employer__user"
        ), pk=message_id)
        ChatService.assert_conversation_access(message.conversation, request.user)
        if not message.attachment:
            raise Http404
        try:
            response = FileResponse(message.attachment.open("rb"), as_attachment=True,
                                    filename=Path(message.attachment.name).name)
        except FileNotFoundError:
            raise Http404 from None
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
