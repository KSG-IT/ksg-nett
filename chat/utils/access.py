from django.utils import timezone
from graphene_django_cud.util import disambiguate_id

from chat.consts import ONLINE_WITHIN
from chat.models import Chat, ChatMembership
from common.exceptions import IllegalOperation


def get_chat(chat_id):
    try:
        return Chat.objects.get(pk=disambiguate_id(chat_id))
    except (Chat.DoesNotExist, ValueError):
        raise IllegalOperation("Chat does not exist")


def readable_chat(user, chat_id):
    """
    The chat if the user is a member or a superuser. Reading has no side
    effect: a superuser who reads a chat is not added, not seen as online and
    does not leave a read marker.
    """
    chat = get_chat(chat_id)
    if (
        user.is_superuser
        or ChatMembership.objects.filter(chat=chat, user=user).exists()
    ):
        return chat
    # The same message as for a missing chat, so ids cannot be probed
    raise IllegalOperation("Chat does not exist")


def is_online(membership, now=None):
    now = now or timezone.now()
    return (
        membership.last_seen_at is not None
        and now - membership.last_seen_at < ONLINE_WITHIN
    )
