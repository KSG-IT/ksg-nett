import secrets


def ical_token_generator(*args, **kwargs):
    return secrets.token_urlsafe(16)
