from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from chat.consts import MAX_MESSAGE_LENGTH, PRESENCE_WRITE_INTERVAL
from chat.models import Chat, ChatMembership, ChatMessage
from common.exceptions import IllegalOperation
from schedules.models import ShiftSlot


def membership_for(user, chat):
    membership = ChatMembership.objects.filter(chat=chat, user=user).first()
    if membership is None:
        raise PermissionDenied("You are not a member of this chat")
    return membership


def role_at(user, now):
    """The user's role on the shift that runs at `now`, or None."""
    slot = (
        ShiftSlot.objects.filter(
            user=user,
            shift__datetime_start__lte=now,
            shift__datetime_end__gte=now,
        )
        .order_by("shift__datetime_start", "id")
        .first()
    )
    return slot.role if slot else None


def send_chat_message(user, chat, body, now=None):
    now = now or timezone.now()
    membership_for(user, chat)
    if now > chat.closes_at:
        raise IllegalOperation("The chat is closed")
    body = (body or "").strip()
    if not 1 <= len(body) <= MAX_MESSAGE_LENGTH:
        raise IllegalOperation(f"A message has 1 to {MAX_MESSAGE_LENGTH} letters")

    with transaction.atomic():
        message = ChatMessage.objects.create(
            chat=chat, sender=user, role=role_at(user, now), body=body
        )
        Chat.objects.filter(pk=chat.pk).update(last_message_at=message.created_at)
    return message


def mark_read(user, chat, message_id):
    """
    Move the read marker forward to this message. It never moves back.
    Returns True when the marker changed.
    """
    membership_for(user, chat)
    message = ChatMessage.objects.filter(pk=message_id, chat=chat).first()
    if message is None:
        raise IllegalOperation("The message is not in this chat")
    changed = (
        ChatMembership.objects.filter(chat=chat, user=user)
        .filter(
            Q(last_read_message__isnull=True) | Q(last_read_message_id__lt=message.pk)
        )
        .update(last_read_message=message)
    )
    return changed > 0


def ping(user, chat, now=None):
    """Record that the member has the chat open. Writes at most every 15 s."""
    now = now or timezone.now()
    membership_for(user, chat)
    changed = (
        ChatMembership.objects.filter(chat=chat, user=user)
        .filter(
            Q(last_seen_at__isnull=True)
            | Q(last_seen_at__lt=now - PRESENCE_WRITE_INTERVAL)
        )
        .update(last_seen_at=now)
    )
    return changed > 0
