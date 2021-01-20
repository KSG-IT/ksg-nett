from ksg_nett.settings import *
import psycopg2
import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'rc4yscfoc9loe+937$q-57agxy0iq+!o0zowl0#vylilol2-)e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["ksg-nett.herokuapp.com"]

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

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')

DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)

# S3 media files
#AWS_REGION = "eu-west-3"
#AWS_S3_BUCKET_AUTH = False
#AWS_S3_BUCKET_NAME = "ksg-nett-bucket"
#DEFAULT_FILE_STORAGE = "django_s3_storage.storage.S3Storage"
#MEDIA_URL = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/"
