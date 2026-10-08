import os

from django.core.exceptions import ImproperlyConfigured


def required_secret(name, min_length=32):
    """
    A secret from the environment. Raises ImproperlyConfigured, so the app
    does not start, when it is missing or shorter than min_length. 32 bytes
    is the minimum for an HS256 key (RFC 7518).
    """
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    if len(value) < min_length:
        raise ImproperlyConfigured(
            f"{name} must be at least {min_length} characters, " f"not {len(value)}."
        )
    return value
