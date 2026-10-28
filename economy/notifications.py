"""
The economy notifications, one function per event, with every channel. The
mutations call these through transaction.on_commit.
"""

from push.utils import PushMessage, send_to_users
from users.models import User


def notify_deposit_approved(deposit):
    """
    E-mail and push "deposit approved" to the owner of the account.
    `notify_on_deposit` decides the e-mail and `push_on_deposit` the push.
    Only manual approvals call this: a card deposit is approved while the user
    watches, and the Stripe webhook sends its own e-mail.
    """
    # economy.utils imports economy.schema, which imports this module
    from economy.utils import send_deposit_approved_email

    user = deposit.account.user
    if user.notify_on_deposit:
        send_deposit_approved_email(deposit)
    if not user.push_on_deposit:
        return
    amount = f"{deposit.amount:,}".replace(",", "\u00a0")
    send_to_users(
        [user.pk],
        PushMessage(
            title="Innskudd godkjent",
            body=f"{amount}\u00a0kr er satt inn på Soci-kontoen din.",
            path="/economy/me",
            tag=f"deposit-{deposit.pk}",
        ),
    )


def notify_order_session_invited(session, user_ids, actor=None):
    """
    E-mail and push "the food list is open" to the invited users. Everyone
    gets the e-mail. The push skips the actor and users with
    `push_on_order_session` off.
    """
    from economy.utils import send_soci_order_session_invitation_email

    invited = User.objects.filter(pk__in=user_ids)
    send_soci_order_session_invitation_email(session, invited)
    users = invited.filter(push_on_order_session=True)
    if actor is not None:
        users = users.exclude(pk=actor.pk)
    recipient_ids = list(users.values_list("pk", flat=True))
    if not recipient_ids:
        return
    send_to_users(
        recipient_ids,
        PushMessage(
            title="Stilletime",
            body="Burgerlista er åpen. Legg inn matbestillingen din.",
            path="/economy/soci-sessions/live",
            tag=f"order-session-{session.pk}",
            urgency="high",
        ),
    )
