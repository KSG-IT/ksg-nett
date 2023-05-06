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


def send_debt_collection_email(user_info):
    """
    User info contains name, email, frontend_url
    """

    content = f"""
        Hei {user_info["name"]}!
        
        Du har en utestående gjeld på KSG-nett. 
        Du kan betale ved å trykke på lenken under:
        {user_info['frontend_url']}
        
        Gjerne si ifra om dette ikke stemmer, så skal vi få ordnet opp i det. 
        Helst ikke svar, eller videresend denne eposten, da den inneholder lenke for å logge inn på din bruker.
        
        Om du skulle ha noen spørsmål, så kan du sende en epost til ksg-soci-okonomi@samfundet.no.
        """

    html_content = f"""
        Hei {user_info["name"]}!
        <br>
        <br>
        Du har en utestående gjeld på KSG-nett.
        <br>
        Du kan betale ved å trykke på lenken under:
        <br>
        <span>{user_info['frontend_url']}</span>
        
        <br>
        <br>
        Gjerne si ifra om dette ikke stemmer, så skal vi få ordnet opp i det.
        <br>
        <br>
        Helst ikke svar, eller videresend denne eposten, da den inneholder lenke for å logge inn på din bruker.
        <br>
        <br>
        Om du skulle ha noen spørsmål, så kan du sende en epost til <a href="mailto:ksg-soci-okonomi@samfundet.no">ksg-soci-okonomi@samfundet.no</a>
               
        
        
    """

    send_email(
        recipients=[user_info["email"]],
        subject="KSG-nett - Utestående gjeld",
        message=content,
        html_message=html_content,
    )
