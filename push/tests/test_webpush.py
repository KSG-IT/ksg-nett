import base64
import copy
import json
import os
from types import SimpleNamespace
from unittest import mock

import http_ece
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from django.test import SimpleTestCase

from push import webpush


def b64url_decode(data):
    data = "".join(data.split())
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def make_browser():
    """The keys a browser hands out in a PushSubscription, and its private key."""
    private = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    return private, b64url_encode(public_bytes(private)), b64url_encode(auth), auth


def vapid_claims(authorization):
    token = authorization.split("t=", 1)[1].split(",", 1)[0]
    return json.loads(b64url_decode(token.split(".")[1]))


def vapid_body(key):
    der = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return base64.b64encode(der).decode("ascii")


# RFC 8291, section 5 and appendix A
RFC_PLAINTEXT = b64url_decode("V2hlbiBJIGdyb3cgdXAsIEkgd2FudCB0byBiZSBhIHdhdGVybWVsb24")
RFC_AS_PRIVATE = b64url_decode("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw")
RFC_UA_PUBLIC = """
    BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcx
    aOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4
"""
RFC_SALT = b64url_decode("DGv6ra1nlYgDCS1FRnbzlw")
RFC_AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
RFC_BODY = b64url_decode("""
    DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27ml
    mlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPT
    pK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN
    """)


class EncryptPayloadTest(SimpleTestCase):
    def test_matches_the_rfc_8291_vector(self):
        as_private = ec.derive_private_key(
            int.from_bytes(RFC_AS_PRIVATE, "big"), ec.SECP256R1()
        )
        body = webpush.encrypt_payload(
            RFC_PLAINTEXT,
            "".join(RFC_UA_PUBLIC.split()),
            RFC_AUTH,
            salt=RFC_SALT,
            as_private=as_private,
        )
        self.assertEqual(body, RFC_BODY)

    def test_round_trips_through_http_ece(self):
        private, p256dh, auth, auth_bytes = make_browser()
        payload = "Ølstua: Hei på deg 🍺".encode()

        body = webpush.encrypt_payload(payload, p256dh, auth)

        decrypted = http_ece.decrypt(
            body, private_key=private, auth_secret=auth_bytes, version="aes128gcm"
        )
        self.assertEqual(decrypted, payload)

    def test_payload_size_boundaries(self):
        private, p256dh, auth, auth_bytes = make_browser()
        for size in (0, 3993):
            body = webpush.encrypt_payload(b"x" * size, p256dh, auth)
            decrypted = http_ece.decrypt(
                body, private_key=private, auth_secret=auth_bytes
            )
            self.assertEqual(len(decrypted), size)
        self.assertEqual(len(body), 4096)

        with self.assertRaises(ValueError):
            webpush.encrypt_payload(b"x" * 3994, p256dh, auth)


class LoadVapidKeyTest(SimpleTestCase):
    def test_loads_the_one_line_base64_body(self):
        key = ec.generate_private_key(ec.SECP256R1())

        loaded = webpush.load_vapid_key(vapid_body(key))

        self.assertEqual(loaded.private_numbers(), key.private_numbers())

    def test_full_pem_raises_a_clear_error(self):
        pem = (
            ec.generate_private_key(ec.SECP256R1())
            .private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            .decode()
        )
        with self.assertRaisesMessage(ValueError, "without the BEGIN and END"):
            webpush.load_vapid_key(pem)


class VapidAuthorizationTest(SimpleTestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())

    def decode(self, authorization):
        scheme, params = authorization.split(" ", 1)
        self.assertEqual(scheme, "vapid")
        token, public_key = (part.split("=", 1)[1] for part in params.split(", "))
        return token, b64url_decode(public_key)

    def test_token_has_header_claims_and_a_valid_raw_signature(self):
        now = 1_800_000_000
        authorization = webpush.vapid_authorization(
            self.key,
            "https://fcm.googleapis.com/fcm/send/abc:def",
            "mailto:it@ksg-nett.no",
            now=now,
        )
        token, public_key = self.decode(authorization)
        header, claims, signature = token.split(".")

        self.assertEqual(
            json.loads(b64url_decode(header)), {"typ": "JWT", "alg": "ES256"}
        )
        claims_json = json.loads(b64url_decode(claims))
        self.assertEqual(claims_json["aud"], "https://fcm.googleapis.com")
        self.assertEqual(claims_json["sub"], "mailto:it@ksg-nett.no")
        self.assertGreater(claims_json["exp"], now)
        self.assertLessEqual(claims_json["exp"], now + 24 * 60 * 60)
        self.assertNotIn("=", token)

        raw = b64url_decode(signature)
        self.assertEqual(len(raw), 64)
        verifier = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), public_key
        )
        verifier.verify(
            encode_dss_signature(
                int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
            ),
            f"{header}.{claims}".encode(),
            ec.ECDSA(hashes.SHA256()),
        )

    def test_two_endpoints_get_their_own_audience(self):
        aud = [
            vapid_claims(
                webpush.vapid_authorization(self.key, endpoint, "mailto:a@b.no")
            )["aud"]
            for endpoint in (
                "https://fcm.googleapis.com/fcm/send/a",
                "https://web.push.apple.com/QGz",
            )
        ]

        self.assertEqual(
            aud, ["https://fcm.googleapis.com", "https://web.push.apple.com"]
        )


class SendTest(SimpleTestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        _, p256dh, auth, _ = make_browser()
        self.subscription = SimpleNamespace(
            endpoint="https://fcm.googleapis.com/fcm/send/abc", p256dh=p256dh, auth=auth
        )

    def send(self, **kwargs):
        options = {"ttl": 3600, "urgency": "normal", "topic": "chat-12", "timeout": 3}
        options.update(kwargs)
        return webpush.send(
            self.subscription, b"{}", self.key, "mailto:a@b.no", **options
        )

    @mock.patch("push.webpush.requests.post")
    def test_posts_encrypted_body_with_push_headers(self, post):
        post.return_value = mock.Mock(status_code=201)

        result = self.send()

        self.assertEqual(result, webpush.SendResult(webpush.OK, 201))
        (endpoint,), kwargs = post.call_args
        self.assertEqual(endpoint, self.subscription.endpoint)
        self.assertIs(kwargs["allow_redirects"], False)
        self.assertEqual(kwargs["timeout"], 3)
        headers = kwargs["headers"]
        self.assertTrue(headers["Authorization"].startswith("vapid t="))
        self.assertEqual(headers["Content-Encoding"], "aes128gcm")
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertEqual(headers["TTL"], "3600")
        self.assertEqual(headers["Urgency"], "normal")
        self.assertEqual(headers["Topic"], "chat-12")

    @mock.patch("push.webpush.requests.post")
    def test_no_topic_header_without_a_topic(self, post):
        post.return_value = mock.Mock(status_code=201)

        self.send(topic=None)

        self.assertNotIn("Topic", post.call_args.kwargs["headers"])

    @mock.patch("push.webpush.requests.post")
    def test_classifies_status_codes(self, post):
        cases = {
            201: webpush.OK,
            404: webpush.GONE,
            410: webpush.GONE,
            400: webpush.REJECTED,
            403: webpush.REJECTED,
            413: webpush.TOO_LARGE,
            429: webpush.RETRY_LATER,
            500: webpush.RETRY_LATER,
        }
        for status_code, status in cases.items():
            with self.subTest(status_code=status_code):
                post.return_value = mock.Mock(status_code=status_code, text="")
                result = self.send()
                self.assertEqual(
                    (result.status, result.status_code), (status, status_code)
                )

    @mock.patch("push.webpush.requests.post")
    def test_a_failure_keeps_the_reason_without_the_endpoint(self, post):
        endpoint_path = "/fcm/send/abc"
        post.return_value = mock.Mock(
            status_code=400,
            text=f'{{"reason": "BadJwtToken",\n "path": "{endpoint_path}"}}'
            + "x" * 300,
        )

        reason = self.send().reason

        self.assertTrue(reason.startswith('{"reason": "BadJwtToken", "path"'))
        self.assertNotIn(endpoint_path, reason)
        self.assertIn("<endpoint>", reason)
        self.assertEqual(len(reason), webpush.MAX_REASON_LENGTH)

    @mock.patch("push.webpush.requests.post")
    def test_a_success_has_no_reason(self, post):
        post.return_value = mock.Mock(status_code=201, text="secret body")

        self.assertIsNone(self.send().reason)

    @mock.patch("push.webpush.requests.post")
    def test_timeout_and_connection_error_are_retry_later(self, post):
        for error in (requests.Timeout, requests.ConnectionError):
            with self.subTest(error=error):
                post.side_effect = error()
                self.assertEqual(self.send(), webpush.SendResult(webpush.RETRY_LATER))

    @mock.patch("push.webpush.requests.post")
    def test_calls_do_not_share_or_change_state(self, post):
        post.return_value = mock.Mock(status_code=201)
        other = SimpleNamespace(
            endpoint="https://web.push.apple.com/QGz",
            p256dh=self.subscription.p256dh,
            auth=self.subscription.auth,
        )
        before = copy.deepcopy((vars(self.subscription), vars(other)))

        webpush.send(
            self.subscription,
            b"{}",
            self.key,
            "mailto:a@b.no",
            ttl=60,
            urgency="high",
            timeout=3,
        )
        webpush.send(
            other, b"{}", self.key, "mailto:a@b.no", ttl=60, urgency="high", timeout=3
        )

        first, second = (call.kwargs["headers"] for call in post.call_args_list)
        self.assertEqual(
            vapid_claims(first["Authorization"])["aud"], "https://fcm.googleapis.com"
        )
        self.assertEqual(
            vapid_claims(second["Authorization"])["aud"], "https://web.push.apple.com"
        )
        self.assertNotIn("Topic", first)
        self.assertEqual((vars(self.subscription), vars(other)), before)


class TopicTest(SimpleTestCase):
    def test_is_32_characters_of_valid_base64url_for_any_name(self):
        # "deposit-1" has 9 characters: as a topic it is not valid base64url
        for name in ("deposit-1", "chat-12345", "chat-1", "x" * 100, "æøå"):
            with self.subTest(name=name):
                value = webpush.topic(name)
                self.assertEqual(len(value), 32)
                self.assertRegex(value, r"^[A-Za-z0-9_-]{32}$")
                self.assertEqual(len(base64.urlsafe_b64decode(value)), 24)

    def test_is_the_same_for_the_same_name_only(self):
        self.assertEqual(webpush.topic("chat-1"), webpush.topic("chat-1"))
        self.assertNotEqual(webpush.topic("chat-1"), webpush.topic("chat-2"))
