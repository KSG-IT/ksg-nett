"""
Web Push to one subscription: RFC 8291 encryption, RFC 8292 VAPID signing and
the HTTP request to the push service.

Pure functions on `cryptography` and `requests`. No Django and no ORM, so the
module can be tested against the RFC vector on its own.
"""

import base64
import functools
import json
import os
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

RECORD_SIZE = 4096
# Push services only promise a 4096-byte body. Minus the header (86), the GCM
# tag (16) and the delimiter (1) that leaves 3993 (RFC 8291 section 4).
MAX_PAYLOAD_BYTES = 3993
SALT_BYTES = 16
VAPID_LIFETIME_SECONDS = 12 * 60 * 60

OK = "ok"
GONE = "gone"
REJECTED = "rejected"
TOO_LARGE = "too_large"
RETRY_LATER = "retry_later"
MAX_REASON_LENGTH = 200


@dataclass(frozen=True)
class SendResult:
    status: str
    status_code: int | None = None
    # The push service's own words on a failure, for the log (see _reason)
    reason: str | None = None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _public_bytes(public_key: ec.EllipticCurvePublicKey) -> bytes:
    return public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(
        ikm
    )


def encrypt_payload(
    payload: bytes,
    p256dh: str,
    auth: str,
    *,
    salt: bytes | None = None,
    as_private: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """
    Encrypt `payload` for the browser keys `p256dh` and `auth` (base64url, as
    the Push API gives them). Returns the aes128gcm body with one record.
    `salt` and `as_private` are for tests only; every message needs fresh ones.
    """
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"Push payload is {len(payload)} bytes, max is {MAX_PAYLOAD_BYTES}"
        )
    ua_public = _b64url_decode(p256dh)
    # Rejects a point that is not on P-256, as RFC 8291 section 7 requires
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    auth_secret = _b64url_decode(auth)
    if salt is None:
        salt = os.urandom(SALT_BYTES)
    if as_private is None:
        as_private = ec.generate_private_key(ec.SECP256R1())
    as_public = _public_bytes(as_private.public_key())

    ecdh_secret = as_private.exchange(ec.ECDH(), ua_key)
    key_info = b"WebPush: info\x00" + ua_public + as_public
    ikm = _hkdf(auth_secret, ecdh_secret, key_info, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    # 0x02 marks the last (and only) record
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)

    header = (
        salt
        + RECORD_SIZE.to_bytes(4, "big")
        + len(as_public).to_bytes(1, "big")
        + as_public
    )
    return header + ciphertext


@functools.lru_cache(maxsize=1)
def load_vapid_key(base64_body: str) -> ec.EllipticCurvePrivateKey:
    """
    Load the VAPID private key from the one-line base64 body of a PKCS#8 PEM
    file (what `vapid --gen` writes, without the BEGIN and END lines).
    """
    if "-----" in base64_body:
        raise ValueError(
            "VAPID private key must be the one-line base64 body of the PEM file, "
            "without the BEGIN and END lines"
        )
    try:
        der = base64.b64decode("".join(base64_body.split()), validate=True)
        key = serialization.load_der_private_key(der, password=None)
    except ValueError as error:
        raise ValueError("VAPID private key is not a base64 PKCS#8 body") from error
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(
        key.curve, ec.SECP256R1
    ):
        raise ValueError("VAPID private key must be a P-256 key")
    return key


def application_server_key(key: ec.EllipticCurvePrivateKey) -> str:
    """The public key of `key` in base64url, as `pushManager.subscribe` takes it."""
    return _b64url_encode(_public_bytes(key.public_key()))


def vapid_authorization(
    key: ec.EllipticCurvePrivateKey,
    endpoint: str,
    subject: str,
    now: float | None = None,
) -> str:
    """
    The `Authorization` header for one request to `endpoint`. `subject` is a
    `mailto:` URI. The token is an ES256 JWT that lives for 12 hours.
    """
    if now is None:
        now = time.time()
    parts = urlsplit(endpoint)
    header = {"typ": "JWT", "alg": "ES256"}
    claims = {
        "aud": f"{parts.scheme}://{parts.netloc}",
        "exp": int(now) + VAPID_LIFETIME_SECONDS,
        "sub": subject,
    }
    signing_input = ".".join(
        _b64url_encode(json.dumps(part, separators=(",", ":")).encode())
        for part in (header, claims)
    )
    # cryptography signs in DER; JWS wants the raw 64 bytes r || s
    r, s = decode_dss_signature(
        key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    )
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    token = f"{signing_input}.{_b64url_encode(signature)}"
    return f"vapid t={token}, k={application_server_key(key)}"


def _classify(status_code: int) -> str:
    if 200 <= status_code < 300:
        return OK
    if status_code in (404, 410):
        return GONE
    if status_code == 413:
        return TOO_LARGE
    if status_code == 429 or status_code >= 500:
        return RETRY_LATER
    # 400, 401, 403, and anything else the push service should not send
    return REJECTED


def _reason(response, endpoint: str) -> str:
    """
    The start of the error body, such as Apple's {"reason":"BadJwtToken"} or
    Mozilla's errno. The endpoint identifies the device, so it is removed.
    """
    text = response.text or ""
    for secret in (endpoint, urlsplit(endpoint).path):
        if secret:
            text = text.replace(secret, "<endpoint>")
    return " ".join(text.split())[:MAX_REASON_LENGTH]


def send(
    subscription,
    payload: bytes,
    key: ec.EllipticCurvePrivateKey,
    subject: str,
    *,
    ttl: int,
    urgency: str,
    topic: str | None = None,
    timeout: float,
) -> SendResult:
    """
    Encrypt `payload` and post it to the push service of `subscription`, which
    is anything with `endpoint`, `p256dh` and `auth`. Returns the result class.
    Only `requests` errors are caught here; the caller handles the rest.
    """
    headers = {
        "Authorization": vapid_authorization(key, subscription.endpoint, subject),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(ttl),
        "Urgency": urgency,
    }
    if topic is not None:
        headers["Topic"] = topic
    body = encrypt_payload(payload, subscription.p256dh, subscription.auth)
    try:
        response = requests.post(
            subscription.endpoint,
            data=body,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.RequestException:
        return SendResult(RETRY_LATER)
    status = _classify(response.status_code)
    if status in (OK, GONE):
        return SendResult(status, response.status_code)
    return SendResult(
        status, response.status_code, _reason(response, subscription.endpoint)
    )
