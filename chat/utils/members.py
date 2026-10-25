from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from chat.models import Chat, ChatMembership
from common.exceptions import IllegalOperation


def add_members(actor, chat, user_ids, now=None):
    """
    Add users to a chat that allows it (a mega chat). The actor needs the
    permission `chat.add_to_mega_chat` and must be a member. Returns the ids
    of the users who were added.
    """
    now = now or timezone.now()
    if not actor.has_perm("chat.add_to_mega_chat"):
        raise PermissionDenied("You cannot add members")
    with transaction.atomic():
        chat = Chat.objects.select_for_update().get(pk=chat.pk)
        if not ChatMembership.objects.filter(chat=chat, user=actor).exists():
            raise PermissionDenied("You are not a member of this chat")
        if not chat.members_editable:
            raise IllegalOperation("Members of this chat cannot be changed")
        if now > chat.closes_at:
            raise IllegalOperation("The chat is closed")

        existing = set(
            ChatMembership.objects.filter(chat=chat).values_list("user_id", flat=True)
        )
        new_ids = [
            user_id for user_id in dict.fromkeys(user_ids) if user_id not in existing
        ]
        ChatMembership.objects.bulk_create(
            ChatMembership(chat=chat, user_id=user_id) for user_id in new_ids
        )
    return new_ids


def set_muted(user, chat, muted):
    """Mute or unmute message pushes for one chat. Only for members."""
    changed = ChatMembership.objects.filter(chat=chat, user=user).update(muted=muted)
    if not changed:
        raise PermissionDenied("You are not a member of this chat")
