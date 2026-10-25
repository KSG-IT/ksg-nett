import os

from django.core.exceptions import ImproperlyConfigured

from push.webpush import application_server_key, load_vapid_key


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


def required_vapid_keys():
    """
    The VAPID key pair for Web Push from the environment, as (public, private).
    Loads the private key once, so a bad value stops the app at startup and
    not at the first push. The public key must belong to the private key.
    """
    private = required_secret("VAPID_PRIVATE_KEY")
    try:
        key = load_vapid_key(private)
    except ValueError as error:
        raise ImproperlyConfigured(f"VAPID_PRIVATE_KEY: {error}") from error
    public = os.environ.get("VAPID_PUBLIC_KEY", "")
    if public != application_server_key(key):
        raise ImproperlyConfigured(
            "VAPID_PUBLIC_KEY is missing or does not belong to VAPID_PRIVATE_KEY."
        )
    return public, private
