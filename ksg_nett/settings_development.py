from ksg_nett.settings import *
import psycopg2
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "rc4yscfoc9loe+937$q-57agxy0iq+!o0zowl0#vylilol2-)e"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["ksg-nett.alexanderorvik.com", "amazonaws.com"]
AUTH_JWT_SECRET = os.environ.get("AUTH_JWT_SECRET")

# Application definition
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN", ""),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)


# S3 media files
# AWS_S3_REGION_NAME = "eu-west-3"
# ¤AWS_S3_BUCKET_AUTH = False
# AWS_S3_BUCKET_NAME = "ksg-nett-bucket"
# AWS_STORAGE_BUCKET_NAME = "ksg-nett-bucket"
# DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
# MEDIA_URL = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/media/"
