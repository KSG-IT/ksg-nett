"""
The chat notifications. The chat mutations call these through
transaction.on_commit, so nothing goes out for a change that was rolled back.
Push is the only channel for chat.
"""

from django.utils import timezone
from graphql_relay import to_global_id

from chat.models import ChatMembership
from chat.utils import is_online
from push.utils import PushMessage, send_to_users
from users.models import User


def chat_message(chat, title, body, urgency="normal"):
    # One tag per chat, so a new push replaces the older one on the device
    return PushMessage(
        title=title,
        body=body,
        path=f"/chat/{to_global_id('ChatNode', chat.pk)}",
        tag=f"chat-{chat.pk}",
        urgency=urgency,
    )


def notify_new_message(message):
    """
    Push a new message to the members who are not online in the chat, except
    the sender, members who muted the chat and users who turned it off.
    """
    chat = message.chat
    memberships = ChatMembership.objects.filter(
        chat=chat, muted=False, user__notify_on_chat_message=True
    ).exclude(user_id=message.sender_id)
    now = timezone.now()
    user_ids = [m.user_id for m in memberships if not is_online(m, now)]
    if not user_ids:
        return
    title = f"{message.sender.first_name} skriver i {chat.name}"
    send_to_users(user_ids, chat_message(chat, title, message.body, urgency="high"))


def notify_added(chat, user_ids, actor=None):
    """
    Push "you were added" to the users, except the actor and users who turned
    it off. A chat mute does not apply: nobody mutes a chat before joining it.
    """
    users = User.objects.filter(pk__in=user_ids, notify_on_chat_added=True)
    if actor is not None:
        users = users.exclude(pk=actor.pk)
    recipient_ids = list(users.values_list("pk", flat=True))
    if not recipient_ids:
        return
    body = (
        f"{actor.first_name} la deg til i chatten"
        if actor is not None
        else "Du ble lagt til i chatten"
    )
    send_to_users(recipient_ids, chat_message(chat, chat.name, body))


def notify_new_chat(chat, creator):
    """Push "you were added" to everyone in a new chat but its creator."""
    user_ids = list(chat.memberships.values_list("user_id", flat=True))
    notify_added(chat, user_ids, creator)
