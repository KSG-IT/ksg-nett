import os
import subprocess

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DSN = "https://b803a49419fa48029eb23004cb67b99d@o487192.ingest.sentry.io/5545712"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_sha():
    """
    The commit the server runs, used as the Sentry release. SENTRY_RELEASE wins
    when set. safe.directory lets the web user read a checkout another user owns.
    """
    if os.environ.get("SENTRY_RELEASE"):
        return os.environ["SENTRY_RELEASE"]
    try:
        result = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", BASE_DIR, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def init_sentry(environment):
    sentry_sdk.init(
        dsn=DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=False,
        environment=environment,
        release=git_sha(),
    )
