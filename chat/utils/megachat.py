"""
A mega chat holds everyone on duty when it is made, and its creator. Users with the permission
`chat.create_mega_chat` can make one on Friday and Saturday evenings. Members
can be added later with `add_members`.
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from chat.consts import (
    CLOSE_AFTER,
    MAX_CHAT_NAME_LENGTH,
    MEGA_CHAT_FROM_HOUR,
    MEGA_CHAT_WEEKDAYS,
)
from chat.models import Chat, ChatMembership
from common.exceptions import IllegalOperation
from schedules.models import ShiftSlot


def is_mega_chat_time(now):
    local = timezone.localtime(now)
    return local.weekday() in MEGA_CHAT_WEEKDAYS and local.hour >= MEGA_CHAT_FROM_HOUR


def on_duty_slots(now):
    """Filled slots on the shifts that run at `now`."""
    return ShiftSlot.objects.filter(
        user__isnull=False,
        shift__datetime_start__lte=now,
        shift__datetime_end__gte=now,
    ).select_related("shift")


def mega_chat_preview(user, now=None):
    """
    What a new mega chat would hold: whether the window is open, and the
    running shifts with their number of users, earliest start first.
    """
    now = now or timezone.now()
    if not user.has_perm("chat.create_mega_chat"):
        raise PermissionDenied("You cannot create a mega chat")
    shifts = {}
    user_ids = set()
    for slot in on_duty_slots(now):
        shift_users = shifts.setdefault(slot.shift, set())
        shift_users.add(slot.user_id)
        user_ids.add(slot.user_id)
    ordered = sorted(
        shifts.items(), key=lambda item: (item[0].datetime_start, item[0].pk)
    )
    return {
        "open": is_mega_chat_time(now),
        "user_count": len(user_ids),
        "shifts": [(shift, len(users)) for shift, users in ordered],
    }


def create_mega_chat(user, name, now=None):
    now = now or timezone.now()
    if not user.has_perm("chat.create_mega_chat"):
        raise PermissionDenied("You cannot create a mega chat")
    if not is_mega_chat_time(now):
        raise IllegalOperation("Mega chats are open on Friday and Saturday evenings")
    name = (name or "").strip()
    if not 1 <= len(name) <= MAX_CHAT_NAME_LENGTH:
        raise IllegalOperation(f"The name must be 1 to {MAX_CHAT_NAME_LENGTH} letters")

    slots = list(on_duty_slots(now))
    if not slots:
        raise IllegalOperation("Nobody is on duty")
    # The creator is always a member, also when they are not on duty, so they
    # can read the chat and add people to it.
    user_ids = {slot.user_id for slot in slots} | {user.pk}
    last_end = max(slot.shift.datetime_end for slot in slots)

    with transaction.atomic():
        chat = Chat.objects.create(
            name=name,
            created_by=user,
            created_at=now,
            closes_at=last_end + CLOSE_AFTER,
            members_editable=True,
        )
        ChatMembership.objects.bulk_create(
            ChatMembership(chat=chat, user_id=user_id) for user_id in user_ids
        )
    return chat
