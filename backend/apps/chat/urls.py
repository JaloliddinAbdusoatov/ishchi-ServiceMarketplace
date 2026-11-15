from django.urls import path
from apps.chat.views import (
    MessageAttachmentView,
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMarkReadView,
    ConversationMessagesView,
)

urlpatterns = [
    path("messages/<uuid:message_id>/attachment/", MessageAttachmentView.as_view(), name="chat-attachment"),
    path("conversations/", ConversationListCreateView.as_view(), name="chat-conversations"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="chat-conversation-detail"),
    path("conversations/<uuid:conversation_id>/messages/", ConversationMessagesView.as_view(), name="chat-messages"),
    path("conversations/<uuid:conversation_id>/read/", ConversationMarkReadView.as_view(), name="chat-mark-read"),
]
