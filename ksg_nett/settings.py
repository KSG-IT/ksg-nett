"""
Django settings for ksg_nett project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
import json
import os
from datetime import timedelta
import warnings
from corsheaders.defaults import default_headers

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "ALEXISTHEGREATEST")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
GRAPHIQL = True

CORS_ORIGIN_ALLOW_HEADERS = list(default_headers)
CORS_ORIGIN_ALLOW_ALL = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "ksg-nett.no",
    "ksg-nett.samfundet.no",
    "ksg-nett-dev.samfundet.no",
    "*.samfundet.no",
]

CORS_ALLOW_HEADERS = [
    "baggage",
    "sentry-trace",
] + CORS_ORIGIN_ALLOW_HEADERS

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
    "drf_yasg",
    "graphene_django",
    "corsheaders",
    "django_filters",
    # Project apps
    "api",
    "bar_tab",
    "common",
    "economy",
    "external",
    "internal",
    "legacy",
    "login",
    "organization",
    "quotes",
    "schedules",
    "summaries",
    "users",
    "sensors",
    "admissions",
    "handbook",
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
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", os.path.join(BASE_DIR, "db.sqlite3")),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
    "ksg_nett.custom_authentication.UsernameOrEmailAuthenticationBackend",
    "ksg_nett.backends.auth_backend.UserTypeBackend",
]

# Default login_required return url
LOGIN_URL = "/"

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Belgrade"
USE_I18N = True
USE_L10N = True
USE_TZ = True

warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

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

HOST_URL = "http://localhost:8000"

MEDIA_ROOT = "media/"
MEDIA_URL = "http://localhost:8000/media/"

APP_URL = "http://localhost:3012"
BASE_URL = "http://localhost:8000"

MAX_MEDIA_SIZE = 128 * (1024**2)

# Given in percentage
APPLICANT_IMAGE_COMPRESSION_VALUE = 50

# Compression
IMAGE_COMPRESSION_VALUE = 80
MAX_PNG_WIDTH = 1200
MAX_PNG_HEIGHT = 1200
PNG_COMPRESSION_LOW_QUALITY = 1200
PNG_COMPRESSION_MEDIUM_QUALITY = 2000
PNG_COMPRESSION_HIGH_QUALITY = 2800

ADMISSION_BOOK_INTERVIEWS_NOW = False
# The late batch is used as a soft limit for what interviews are bookable first
ADMISSION_LATE_BATCH_TIMESTAMP = timedelta(hours=15)

# Simple JWT SETTINGS
# -----------------------------
#

AUTH_JWT_HEADER_PREFIX = "Bearer"
AUTH_JWT_SECRET = "SOME-JWT-SECRET-VALUE"
AUTH_JWT_METHOD = "HS256"

SIMPLE_JWT = {
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.SlidingToken",),
    "ALGORITHM": AUTH_JWT_METHOD,
    "SIGNING_KEY": AUTH_JWT_SECRET,
    "SLIDING_TOKEN_LIFETIME": timedelta(
        hours=24
    ),  # Should cover even the most hardcore Soci sessions
    "AUTH_HEADER_TYPES": ("JWT",),
}
# Sensor token. This is used to authenticate incoming sensor API requests.
# This should be changed before production.
SENSOR_API_TOKEN = os.environ.get("SENSOR_API_TOKEN", "3@Zhg$nH^Dlhw23R")

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
WANTED_LIST_THRESHOLD = -2000
OWES_MONEY_THRESHOLD = 0
SOCI_GOLD = []
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", None)
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", None)
STRIPE_FLAT_FEE = 2  # in NOK
STRIPE_PERCENTAGE_FEE = 2.4

DEPOSIT_TIME_RESTRICTION_HOUR = os.environ.get("DEPOSIT_TIME_RESTRICTION_HOUR", 20)
LANGUAGE_SESSION_KEY = "language"

VERSION = "2023.8.2"

# Feature flag keys
STRIPE_INTEGRATION_FEATURE_FLAG = "stripe_integration"
BANK_TRANSFER_DEPOSIT_FEATURE_FLAG = "bank_transfer_deposit"
DEPOSIT_TIME_RESTRICTIONS_FEATURE_FLAG = "deposit_time_restrictions"
EXTERNAL_CHARGING_FEATURE_FLAG = "external_charging"

EXTERNAL_CHARGE_MAX_AMOUNT = os.environ.get("EXTERNAL_CHARGE_MAX_AMOUNT", 300)

# Channels
ASGI_APPLICATION = "ksg_nett.routing.application"
# ASGI_APPLICATION = "ksg_nett.asgi.application"
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

DEVELOPMENT = os.getenv("DEVELOPMENT", "False") == "True"
if DEVELOPMENT:
    try:
        from .settings_development import *
    except ImportError:
        pass

PRODUCTION = os.getenv("PRODUCTION", "False") == "True"
if PRODUCTION:
    try:
        from .settings_prod import *
    except ImportError:
        pass
