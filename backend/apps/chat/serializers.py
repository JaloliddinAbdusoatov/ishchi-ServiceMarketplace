from django.urls import reverse
from rest_framework import serializers
from apps.chat.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    attachment = serializers.SerializerMethodField()

    def get_attachment(self, obj):
        return reverse("api-v1:chat-attachment", kwargs={"message_id": obj.pk}) if obj.attachment else None

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_id",
            "sender_name",
            "content",
            "attachment",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True, default="", max_length=5000)
    attachment = serializers.FileField(required=False, allow_null=True)

    def validate_attachment(self, value):
        if value:
            from apps.common.validators import validate_chat_attachment
            validate_chat_attachment(value)
        return value


class ConversationCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
    worker = serializers.UUIDField(required=False, allow_null=True)


class ConversationSerializer(serializers.ModelSerializer):
    order_title = serializers.CharField(source="order.title", read_only=True)
    employer_name = serializers.CharField(source="employer.full_name", read_only=True)
    worker_name = serializers.CharField(source="worker.full_name", read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "order",
            "order_title",
            "employer",
            "employer_name",
            "worker",
            "worker_name",
            "last_message_at",
            "unread_count",
            "last_message",
            "created_at",
        ]
        read_only_fields = fields

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if not msg:
            return None
        return {
            "id": str(msg.id),
            "sender_id": str(msg.sender_id),
            "content": msg.content,
            "has_attachment": bool(msg.attachment),
            "created_at": msg.created_at,
        }
