"""
The economy notifications, one function per event, with every channel. The
mutations call these through transaction.on_commit.
"""

from push.utils import PushMessage, send_to_users


def notify_deposit_approved(deposit):
    """
    E-mail and push "deposit approved" to the owner of the account. The
    setting `notify_on_deposit` decides both. Only manual approvals call this:
    a card deposit is approved while the user watches, and the Stripe webhook
    sends its own e-mail.
    """
    # economy.utils imports economy.schema, which imports this module
    from economy.utils import send_deposit_approved_email

    user = deposit.account.user
    if not user.notify_on_deposit:
        return
    send_deposit_approved_email(deposit)
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
