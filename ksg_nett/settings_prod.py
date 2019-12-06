import os
from ksg_nett.settings import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'rc4yscfoc9loe+937$q-57agxy0iq+!o0zowl0#vylilol2-)e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [".alexanderorvik.com"]

# Application definition
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get("DB_NAME"),
        'USER': os.environ.get("DB_USER"),
        'PASSWORD': os.environ.get("DB_PASSWORD"),
        'HOST': os.environ.get("DB_HOST"),
        'PORT': os.environ.get("DB_PORT"),
    }
}

# S3 media files
AWS_REGION = "eu-west-3"
AWS_S3_BUCKET_AUTH = False

AWS_S3_BUCKET_NAME = "ksg-nett-bucket"
DEFAULT_FILE_STORAGE = "django_s3_storage.storage.S3Storage"
MEDIA_URL = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/"

# Password validation

# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

# TODO: In case you didn't know, 6 characters is not enough nowadays...
# TODO: This should obviously be changed before production

if not DEBUG:
    AUTH_PASSWORD_VALIDATORS += [
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]
# Override in production
LOCALE_PATHS = ['locales/', ]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

# API DOCS
# ------------------------------
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'api.api_docs.CustomSwaggerAutoSchema',
}

REDOC_SETTINGS = {
    'PATH_IN_MIDDLE': True,
    'REQUIRED_PROPS_FIRST': True
}

# ECONOMY SETTINGS
# ------------------------------
SOCI_MASTER_ACCOUNT_CARD_ID = 0xBADCAFEBABE  # Real card ids are 10 digits, while this is 14, meaning no collisions
DIRECT_CHARGE_SKU = "X-BELOP"


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)]
        }
    }
}


# Redis
REDIS = {
    'host': 'localhost',
    'port': 6379
}
CHAT_STATE_REDIS_DB = 1


