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
