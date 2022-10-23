import jwt
from django.conf import settings
from django.utils import timezone


def create_jwt_token_for_user(user, expiry_in_days=30, secret=None, method=None):
    token_data = {"id": user.id, "iat": timezone.now(), "iss": "KSG-nett"}

    if secret is None:
        secret = settings.AUTH_JWT_SECRET

    if method is None:
        method = settings.AUTH_JWT_METHOD

    if expiry_in_days is not None:
        token_data["exp"] = timezone.now() + timezone.timedelta(days=expiry_in_days)

    token = jwt.encode(token_data, secret, algorithm=method)
    return token


def send_password_reset_email(user, token):
    """
    Sends a password reset email to the user.
    :param user: The user to send the email to.
    :param token: The token to send in the email.
    :return:
    """
    from django.utils.html import strip_tags
    from common.util import send_email

    content = f"""
        Hei!
        
        Vi har mottatt en forespørsel om å nullstille passordet ditt. 
        
        For å nullstille passordet ditt, trykk på lenken under:
        {settings.APP_URL}/reset-password?token={token}
        """

    html_content = f"""
                Hei! 
                <br>
                <br>
                Vi har mottatt en forespørsel om å nullstille passordet ditt.
                <br>
                <br>
                <a href="{settings.APP_URL}/reset-password?token={token}">Klikk her for å nullstille passordet ditt</a>
            """
    subject = "KSG-nett - Nullstill passord"
    send_email(
        subject=subject,
        message=content,
        html_message=html_content,
        recipients=[user.email],
    )
