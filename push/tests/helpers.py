import base64
from itertools import count

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from push.models import PushSubscription
from push.webpush import application_server_key

ENDPOINTS = count()


def make_vapid_keys():
    """A VAPID key pair as the settings hold it: (public, private)."""
    key = ec.generate_private_key(ec.SECP256R1())
    der = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return application_server_key(key), base64.b64encode(der).decode()


VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY = make_vapid_keys()


def make_subscription(user):
    """A subscription with real browser keys, so the payload encrypts."""
    browser = ec.generate_private_key(ec.SECP256R1())
    return PushSubscription.objects.create(
        user=user,
        endpoint=f"https://fcm.googleapis.com/fcm/send/{next(ENDPOINTS)}",
        p256dh=application_server_key(browser),
        auth=base64.urlsafe_b64encode(b"0123456789abcdef").rstrip(b"=").decode(),
    )
