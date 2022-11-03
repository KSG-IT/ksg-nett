import secrets


def ical_token_generator(*args, **kwargs):
    from .models import User

    while True:
        token = secrets.token_urlsafe(16)
        exists = User.objects.filter(ical_token=token).exists()
        if not exists:
            return token
