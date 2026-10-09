import os
from ksg_nett.settings import *
from ksg_nett.env import required_secret
from ksg_nett.sentry import init_sentry

# Raise exceptions on unhandled secret key
SECRET_KEY = os.environ.get("SECRET_KEY", None)

# The app does not start without a real JWT key (ksg_nett/env.py).
AUTH_JWT_SECRET = required_secret("AUTH_JWT_SECRET")
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": AUTH_JWT_SECRET}

DEBUG = False
GRAPHIQL = False
EMAIL_HOST = "smtp.samfundet.no"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
SERVER_EMAIL = "ksg-nett-no-reply@samfundet.no"
DEFAULT_FROM_EMAIL = "ksg-nett-no-reply@samfundet.no"

init_sentry("production")

HOST_URL = "https://ksg-nett.samfundet.no"
MEDIA_URL = "https://ksg-nett.samfundet.no/media/"
APP_URL = "app.ksg-nett.no"
BASE_URL = "https://ksg-nett.samfundet.no"

SILENCED_SYSTEM_CHECKS = ["fields.W161"]

# When False can only book interviews after midnight of current day
ADMISSION_BOOK_INTERVIEWS_NOW = False
OWES_MONEY_THRESHOLD = 0

# Django mails ADMINS on server errors. Sentry reports errors, so leave it empty.
ADMINS = []

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
