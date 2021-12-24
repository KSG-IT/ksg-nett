import os
from ksg_nett.settings import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "rc4yscfoc9loe+937$q-57agxy0iq+!o0zowl0#vylilol2-)e"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [".alexanderorvik.com", ".amazonaws.com", "ksg-nett.no"]
AUTH_JWT_SECRET = os.environ.get("AUTH_JWT_SECRET")

# Application definition
# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql_psycopg2',
#        'NAME': os.environ.get("DB_NAME"),
#        'USER': os.environ.get("DB_USER"),
#        'PASSWORD': os.environ.get("DB_PASSWORD"),
#        'HOST': os.environ.get("DB_HOST"),
#        'PORT': os.environ.get("DB_PORT"),
#    }
# }

# S3 media files
# AWS_REGION = "eu-west-3"
# AWS_S3_BUCKET_AUTH = False
# AWS_S3_BUCKET_NAME = "ksg-nett-bucket"
# DEFAULT_FILE_STORAGE = "django_s3_storage.storage.S3Storage"
# MEDIA_URL = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/"

AWS_STORAGE_BUCKET_NAME = "ksg-nett-bucket"
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
