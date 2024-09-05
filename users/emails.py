from django.conf import settings


def welcome_single_user_email(user_email, jwt_token):
    from common.util import send_email

    content = f"""
        Hei!
        
        Velkommen til KSG! Første gang du logger inn må du sette et passord. 
        
        For å sette passordet ditt, trykk på lenken under:
        {settings.APP_URL}/reset-password?token={jwt_token}
        """

    html_content = f"""
                Hei! 
                <br>
                <br>
                Velkommen til KSG! Første gang du logger inn må du sette et passord. 
                <br>
                <br>
                <span>{settings.APP_URL}/reset-password?token={jwt_token}</span>
            """
    subject = "Velkommen til KSG!"
    send_email(
        subject=subject,
        message=content,
        html_message=html_content,
        recipients=[user_email],
    )
