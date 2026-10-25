"""
The pushes. The mutations call these through transaction.on_commit, so a push
never goes out for a change that was rolled back.
"""

from django.conf import settings
from django.utils import timezone
from graphql_relay import to_global_id

from chat.models import ChatMembership
from chat.utils import is_online
from common.util import check_feature_flag
from push.utils import app_url, send_to_users
from users.models import User

MAX_BODY_LENGTH = 140


def chat_payload(chat, body):
    """Declarative Web Push JSON. Safari shows it without the service worker."""
    if len(body) > MAX_BODY_LENGTH:
        body = body[: MAX_BODY_LENGTH - 1] + "…"
    return {
        "web_push": 8030,
        "notification": {
            "title": chat.name,
            "body": body,
            "navigate": app_url(f"/chat/{to_global_id('ChatNode', chat.pk)}"),
            # One notification per chat: a new push replaces the old one
            "tag": chat_topic(chat),
            "lang": "nb",
        },
    }


def chat_topic(chat):
    return f"chat-{chat.pk}"


def notify_chat_message(message):
    """
    Push a new message to the members who are not online in the chat, except
    the sender, members who muted the chat and users who turned it off.
    """
    if not check_feature_flag(settings.PUSH_FEATURE_FLAG, fail_silently=True):
        return
    chat = message.chat
    memberships = ChatMembership.objects.filter(
        chat=chat, muted=False, user__notify_on_chat_message=True
    ).exclude(user_id=message.sender_id)
    now = timezone.now()
    user_ids = [m.user_id for m in memberships if not is_online(m, now)]
    if not user_ids:
        return
    send_to_users(
        user_ids,
        chat_payload(chat, f"{message.sender.first_name}: {message.body}"),
        topic=chat_topic(chat),
        urgency="high",
    )


def notify_chat_added(chat, user_ids, actor=None):
    """
    Push "you were added" to the users, except the actor and users who turned
    it off. A chat mute does not apply: nobody mutes a chat before joining it.
    """
    if not check_feature_flag(settings.PUSH_FEATURE_FLAG, fail_silently=True):
        return
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
    send_to_users(recipient_ids, chat_payload(chat, body), topic=chat_topic(chat))


def notify_deposit_approved(deposit):
    """
    Push "deposit approved" to the owner of the account. The e-mail setting
    `notify_on_deposit` decides, the same as for the e-mail. Only manual
    approvals call this: a card deposit is approved while the user watches.
    """
    if not check_feature_flag(settings.PUSH_FEATURE_FLAG, fail_silently=True):
        return
    user = deposit.account.user
    if not user.notify_on_deposit:
        return
    amount = f"{deposit.amount:,}".replace(",", "\u00a0")
    payload = {
        "web_push": 8030,
        "notification": {
            "title": "Innskudd godkjent",
            "body": f"{amount}\u00a0kr er satt inn på Soci-kontoen din.",
            "navigate": app_url("/economy/me"),
            "tag": f"deposit-{deposit.pk}",
            "lang": "nb",
        },
    }
    send_to_users([user.pk], payload, topic=f"deposit-{deposit.pk}")
