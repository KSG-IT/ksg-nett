"""
Shift chats. A shift chat has no link to its shift. It is the chat created in
the join window of the shift whose members are exactly the users on the
shift. Nobody changes its members by hand. Shifts are planned in advance and
rarely change during the join window, so the chat does not follow later roster
changes. If the roster changes after the chat exists, the next click makes a
new chat.
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from chat.consts import (
    CLOSE_AFTER,
    JOIN_AFTER,
    JOIN_BEFORE,
    MIN_SHIFT_CHAT_USERS,
)
from chat.models import Chat, ChatMembership
from common.exceptions import IllegalOperation
from schedules.models import Shift, ShiftSlot


def assigned_user_ids(shift):
    return frozenset(
        ShiftSlot.objects.filter(shift=shift, user__isnull=False).values_list(
            "user_id", flat=True
        )
    )


def join_window(shift):
    return shift.datetime_start - JOIN_BEFORE, shift.datetime_end + JOIN_AFTER


def find_shift_chat(shift, user_ids):
    """The chat made in the join window with exactly these members, or None."""
    if not user_ids:
        return None
    start, end = join_window(shift)
    ids = list(user_ids)
    return (
        Chat.objects.filter(created_at__gte=start, created_at__lte=end)
        .annotate(
            member_count=Count("memberships", distinct=True),
            matching=Count(
                "memberships", filter=Q(memberships__user_id__in=ids), distinct=True
            ),
        )
        .filter(member_count=len(ids), matching=len(ids))
        .order_by("created_at")
        .first()
    )


def fetch_chat_for_shift(user, shift, now=None):
    """
    The chat of a shift for a user who works on it. The first call creates the
    chat with all users on the shift. Later calls return the same chat.
    The lock on the shift row makes two clicks at the same moment safe.
    Returns (chat, created).
    """
    now = now or timezone.now()
    with transaction.atomic():
        shift = Shift.objects.select_for_update().get(pk=shift.pk)
        user_ids = assigned_user_ids(shift)
        if user.pk not in user_ids:
            raise PermissionDenied("You are not on this shift")
        if len(user_ids) < MIN_SHIFT_CHAT_USERS:
            raise IllegalOperation("The shift has too few users for a chat")
        start, end = join_window(shift)
        if not start <= now <= end:
            raise IllegalOperation("The chat of this shift is not open for joining")

        chat = find_shift_chat(shift, user_ids)
        if chat is not None:
            return chat, False
        chat = Chat.objects.create(
            name=f"{shift.name} gruppechat",
            created_by=user,
            closes_at=shift.datetime_end + CLOSE_AFTER,
        )
        ChatMembership.objects.bulk_create(
            ChatMembership(chat=chat, user_id=user_id) for user_id in user_ids
        )
        return chat, True


def joinable_shift_chats(user, now=None):
    """
    The shifts the user may open a chat for right now, each with its chat or
    None. A shift qualifies when the user works on it, it has enough users and
    the join window is open.
    """
    now = now or timezone.now()
    shifts = (
        Shift.objects.filter(
            pk__in=ShiftSlot.objects.filter(user=user).values("shift_id"),
            datetime_start__lte=now + JOIN_BEFORE,
            datetime_end__gte=now - JOIN_AFTER,
        )
        .annotate(user_count=Count("slots", filter=Q(slots__user__isnull=False)))
        .filter(user_count__gte=MIN_SHIFT_CHAT_USERS)
        .order_by("datetime_start", "id")
    )
    return [
        (shift, find_shift_chat(shift, assigned_user_ids(shift))) for shift in shifts
    ]
