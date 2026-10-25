import base64
import os
import subprocess
import sys
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from ksg_nett.env import required_secret, required_vapid_keys
from push.webpush import application_server_key

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LONG_SECRET = "s" * 40


def make_vapid_env():
    key = ec.generate_private_key(ec.SECP256R1())
    der = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return {
        "VAPID_PUBLIC_KEY": application_server_key(key),
        "VAPID_PRIVATE_KEY": base64.b64encode(der).decode(),
    }


VAPID_ENV = make_vapid_env()


def start_django(env):
    """Starts Django in a new process with the given environment, and prints
    the JWT keys it uses."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "print(settings.AUTH_JWT_SECRET); "
            "print(settings.SIMPLE_JWT['SIGNING_KEY'])",
        ],
        cwd=PROJECT_ROOT,
        env={
            "PATH": os.environ.get("PATH", ""),
            "DJANGO_SETTINGS_MODULE": "ksg_nett.settings",
            "SECRET_KEY": "test-secret-key",
            **env,
        },
        capture_output=True,
        text=True,
        timeout=60,
    )


class RequiredSecretTest(SimpleTestCase):
    def test__returns_the_value(self):
        os.environ["KSG_TEST_SECRET"] = LONG_SECRET
        try:
            self.assertEqual(required_secret("KSG_TEST_SECRET"), LONG_SECRET)
        finally:
            del os.environ["KSG_TEST_SECRET"]

    def test__missing__raises(self):
        os.environ.pop("KSG_TEST_SECRET", None)
        with self.assertRaisesMessage(ImproperlyConfigured, "KSG_TEST_SECRET"):
            required_secret("KSG_TEST_SECRET")

    def test__too_short__raises(self):
        os.environ["KSG_TEST_SECRET"] = "short"
        try:
            with self.assertRaisesMessage(ImproperlyConfigured, "at least 32"):
                required_secret("KSG_TEST_SECRET")
        finally:
            del os.environ["KSG_TEST_SECRET"]


class JwtSecretSettingsTest(SimpleTestCase):
    def test__test_settings_sign_both_token_types_with_one_key(self):
        self.assertEqual(settings.SIMPLE_JWT["SIGNING_KEY"], settings.AUTH_JWT_SECRET)
        self.assertGreaterEqual(len(settings.AUTH_JWT_SECRET), 32)

    def test__production_refuses_to_start_without_the_secret(self):
        result = start_django({"PRODUCTION": "True"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AUTH_JWT_SECRET", result.stderr)

    def test__production_uses_the_secret_from_the_environment(self):
        result = start_django(
            {"PRODUCTION": "True", "AUTH_JWT_SECRET": LONG_SECRET, **VAPID_ENV}
        )

        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.split(), [LONG_SECRET, LONG_SECRET])

    def test__development_refuses_to_start_without_the_secret(self):
        result = start_django({"DEVELOPMENT": "True"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AUTH_JWT_SECRET", result.stderr)


class VapidKeySettingsTest(SimpleTestCase):
    def test__production_refuses_to_start_without_the_vapid_key(self):
        result = start_django({"PRODUCTION": "True", "AUTH_JWT_SECRET": LONG_SECRET})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("VAPID_PRIVATE_KEY", result.stderr)

    def test__returns_the_key_pair(self):
        with mock.patch.dict(os.environ, VAPID_ENV):
            self.assertEqual(
                required_vapid_keys(),
                (VAPID_ENV["VAPID_PUBLIC_KEY"], VAPID_ENV["VAPID_PRIVATE_KEY"]),
            )

    def test__a_full_pem_file_raises(self):
        pem = "-----BEGIN PRIVATE KEY-----\n" + VAPID_ENV["VAPID_PRIVATE_KEY"]
        with mock.patch.dict(os.environ, {**VAPID_ENV, "VAPID_PRIVATE_KEY": pem}):
            with self.assertRaisesMessage(ImproperlyConfigured, "BEGIN and END"):
                required_vapid_keys()

    def test__a_public_key_from_another_pair_raises(self):
        other = make_vapid_env()["VAPID_PUBLIC_KEY"]
        with mock.patch.dict(os.environ, {**VAPID_ENV, "VAPID_PUBLIC_KEY": other}):
            with self.assertRaisesMessage(ImproperlyConfigured, "does not belong"):
                required_vapid_keys()
