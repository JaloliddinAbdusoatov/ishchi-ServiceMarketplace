"""Ephemeral tests for visible chat history; no working DB or schema changes."""
import pytest
from django.utils import timezone
from apps.applications.models import OrderApplication
from apps.chat.models import Conversation, Message


def conversation_for(order, worker):
    user, profile = worker
    OrderApplication.objects.create(order=order, worker=profile, proposed_price="100000.00")
    return Conversation.objects.create(order=order, employer=order.employer, worker=profile), user


@pytest.mark.django_db
def test_newest_chat_page_keeps_showing_new_messages_after_one_hundred(auth_client, unverified_worker, published_order):
    conversation, worker = conversation_for(published_order, unverified_worker)
    messages = Message.objects.bulk_create([
        Message(conversation=conversation, sender=worker, content=f"History message {number}") for number in range(101)
    ])
    client = auth_client(worker)
    path = f"/api/v1/chat/conversations/{conversation.pk}/messages/"
    # Existing clients retain chronological default behavior.
    original = client.get(path, {"page_size":100})
    assert original.status_code == 200 and original.data["results"][0]["id"] == str(messages[0].pk)
    latest = Message.objects.create(conversation=conversation, sender=worker, content="New message beyond first hundred")
    newest = client.get(path, {"page_size":100, "ordering":"-created_at"})
    older = client.get(path, {"page_size":100, "ordering":"-created_at", "page":2})
    assert newest.status_code == older.status_code == 200
    assert newest.data["results"][0]["id"] == str(latest.pk)
    ids = [message["id"] for message in newest.data["results"] + older.data["results"]]
    assert len(ids) == len(set(ids)) == 102
    assert str(messages[0].pk) in ids


@pytest.mark.django_db
def test_chat_history_pages_have_stable_tie_breaking_and_keep_authorization(auth_client, unverified_worker, published_order, employer_pair):
    conversation, worker = conversation_for(published_order, unverified_worker)
    Message.objects.bulk_create([
        Message(conversation=conversation, sender=worker, content=f"Same timestamp {number}") for number in range(6)
    ])
    conversation.messages.update(created_at=timezone.now())
    expected = [str(pk) for pk in conversation.messages.order_by("-created_at", "-id").values_list("id", flat=True)]
    path = f"/api/v1/chat/conversations/{conversation.pk}/messages/"
    client = auth_client(employer_pair[0])
    pages = [client.get(path, {"page_size":3, "ordering":"-created_at", "page":page}) for page in (1,2)]
    assert all(response.status_code == 200 for response in pages)
    assert [row["id"] for response in pages for row in response.data["results"]] == expected
    from tests.conftest import UserFactory
    outsider = auth_client(UserFactory())
    assert outsider.get(path, {"ordering":"-created_at"}).status_code == 403
