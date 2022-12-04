from ksg_nett.settings import *
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


DEBUG = True

sentry_sdk.init(
    dsn="https://b803a49419fa48029eb23004cb67b99d@o487192.ingest.sentry.io/5545712",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
    environment="development",
)

EMAIL_HOST = "smtp.samfundet.no"
EMAIL_USE_TLS = True
EMAIL_PORT = 587

HOST_URL = "https://ksg-nett.samfundet.no"
MEDIA_ROOT = "media/"
MEDIA_URL = "https://ksg-nett.samfundet.no/media/"
APP_URL = "app.ksg-nett.no"
BASE_URL = "https://ksg-nett.samfundet.no"

# Application definition
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    },
    "legacy": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME_LEGACY"),
        "USER": os.environ.get("DB_USER_LEGACY"),
        "PASSWORD": os.environ.get("DB_PASSWORD_LEGACY"),
        "HOST": os.environ.get("DB_HOST_LEGACY"),
        "PORT": os.environ.get("DB_PORT_LEGACY"),
    },
}
