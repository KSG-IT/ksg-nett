"""
Django settings for ksg_nett project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
from datetime import timedelta

from corsheaders.defaults import default_headers

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "rc4yscfoc9loe+937$q-57agxy0iq+!o0zowl0#vylilol2-)e"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


CORS_ORIGIN_ALLOW_ALL = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "ksg-nett.no"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_yasg2",
    "graphene_django",
    "storages",
    "corsheaders",
    # Project apps
    "api",
    "common",
    "economy",
    "external",
    "internal",
    "login",
    "organization",
    "quotes",
    "schedules",
    "summaries",
    "users",
    "sensors",
    "chat",
    "admissions",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "login.middleware.JwtProviderMiddleware",
]

ROOT_URLCONF = "ksg_nett.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.internal_groups",
            ],
        },
    }
]

WSGI_APPLICATION = "ksg_nett.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# Default from pre 3.2. Possible to change to BigAutoField
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

# TODO: In case you didn't know, 6 characters is not enough nowadays...
# TODO: This should obviously be changed before production
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 6,
        },
    },
]
if not DEBUG:
    AUTH_PASSWORD_VALIDATORS += [
        {
            "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]

# Custom user
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "ksg_nett.custom_authentication.UsernameOrEmailAuthenticationBackend"
]

# Default login_required return url
LOGIN_URL = "/"

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Override in production
LOCALE_PATHS = [
    "locales/",
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/


# Django REST framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        # 'rest_framework.permissions.IsAdminUser',
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Graphql
GRAPHENE = {"SCHEMA": "ksg_nett.schema.schema"}


# Media
STATIC_URL = "/static/"
STATIC_ROOT = "static/"

MEDIA_ROOT = "media/"
MEDIA_URL = "http://localhost:8000/media/"
MAX_MEDIA_SIZE = 128 * (1024 ** 2)

# Simple JWT SETTINGS
# ------------------------------
SIMPLE_JWT = {
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.SlidingToken",),
    "SLIDING_TOKEN_LIFETIME": timedelta(
        hours=24
    ),  # Should cover even the most hardcore Soci sessions
    "AUTH_HEADER_TYPES": ("JWT",),
}
# Sensor token. This is used to authenticate incoming sensor API requests.
# This should be changed before production.
SENSOR_API_TOKEN = "3@Zhg$nH^Dlhw23R"

AUTH_JWT_HEADER_PREFIX = "Bearer"
AUTH_JWT_SECRET = "SOME-JWT-SECRET-VALUE"
AUTH_JWT_METHOD = "HS256"

# API DOCS
# ------------------------------
SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "api.api_docs.CustomSwaggerAutoSchema",
}

REDOC_SETTINGS = {"PATH_IN_MIDDLE": True, "REQUIRED_PROPS_FIRST": True}

# ECONOMY SETTINGS
# ------------------------------
SOCI_MASTER_ACCOUNT_CARD_ID = 0xBADCAFEBABE  # Real card ids are 10 digits, while this is 14, meaning no collisions
DIRECT_CHARGE_SKU = "X-BELOP"

# Channels
ASGI_APPLICATION = "ksg_nett.routing.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [os.environ.get("REDIS_URI", ("localhost", 6379))]},
    }
}


# Redis
REDIS = {
    "host": os.environ.get("REDIS_HOST", "localhost"),
    "port": os.environ.get("REDIS_PORT", 6379),
}
CHAT_STATE_REDIS_DB = 1


# Load local and production settings
try:
    from .settings_local import *
except ImportError:
    pass

if "STAGING" in os.environ:
    try:
        from .settings_staging import *
    except ImportError:
        pass
