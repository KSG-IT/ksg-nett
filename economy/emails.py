from common.util import send_email


def send_deposit_invalidated_email(deposit):
    email_list = [deposit.account.user.email]

    content = f"""
        Hei!

        Ditt innskudd på {deposit.resolved_amount} kr har blitt underkjent.
        """

    html_content = f"""
        Hei!
        <br>
        <br>
        
        Ditt innskudd på {deposit.resolved_amount} kr har blitt underkjent.
    """

    send_email(
        recipients=email_list,
        subject="Innskudd underkjent",
        message=content,
        html_message=html_content,
    )
