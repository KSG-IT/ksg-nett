import os
import subprocess
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from ksg_nett.env import required_secret

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LONG_SECRET = "s" * 40


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
        result = start_django({"PRODUCTION": "True", "AUTH_JWT_SECRET": LONG_SECRET})

        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.split(), [LONG_SECRET, LONG_SECRET])

    def test__development_refuses_to_start_without_the_secret(self):
        result = start_django({"DEVELOPMENT": "True"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AUTH_JWT_SECRET", result.stderr)
