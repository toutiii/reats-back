"""
Django settings for reats project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load all env vars in .env
load_dotenv(os.path.join(BASE_DIR, ".env"))

boto3.set_stream_logger(name="botocore.credentials", level=logging.ERROR)
session = boto3.session.Session()

ssm_client = boto3.client("ssm", region_name=os.getenv("AWS_REGION"))
boto3_logs_client = boto3.client("logs", region_name=os.getenv("AWS_REGION"))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ["DEBUG"]

SECRET_KEY = os.getenv("SECRET_KEY")


ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(" ")

# Application definition

INSTALLED_APPS = [
    "django_extensions",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "customer_app",
    "cooker_app",
    "delivery_app",
    "core_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "source.urls"

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
            ],
        },
    },
]


WSGI_APPLICATION = "source.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases


DATABASES = {
    "default": {
        "ENGINE": os.environ["DB_ENGINE"],
        "PORT": os.environ["DB_PORT"],
    }
}

if os.environ["ENV"] != "local":
    DATABASES["default"]["HOST"] = os.environ["RDS_HOST"]
    DATABASES["default"]["USER"] = os.environ["RDS_USER"]
    DATABASES["default"]["PASSWORD"] = os.environ["RDS_PASSWORD"]
    DATABASES["default"]["NAME"] = os.environ["RDS_DB"]
else:
    DATABASES["default"]["HOST"] = os.environ["DB_HOST"]
    DATABASES["default"]["USER"] = os.environ["POSTGRES_USER"]
    DATABASES["default"]["PASSWORD"] = os.environ["POSTGRES_PASSWORD"]
    DATABASES["default"]["NAME"] = os.environ["POSTGRES_DB"]

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = os.path.join(BASE_DIR, "staticfiles/")

PHONE_REGION = "FR"
PHONE_BLACK_LIST = ("0000000000",)  # Check if we need to add more numbers

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "utils.custom_middlewares.custom_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("utils.custom_permissions.UserPermission",),
}

try:
    response = ssm_client.get_parameter(
        Name=os.getenv("RSA_PRIVATE_KEY_PATH"), WithDecryption=False
    )
except ClientError as e:
    raise e

secret_key = response["Parameter"]["Value"]

try:
    response = ssm_client.get_parameter(
        Name=os.getenv("RSA_PUBLIC_KEY_PATH"), WithDecryption=False
    )
except ClientError as e:
    raise e

verifying_key = response["Parameter"]["Value"]


try:
    response = ssm_client.get_parameter(
        Name=os.getenv("AWS_API_KEY_COOKER_APP"), WithDecryption=False
    )
except ClientError as e:
    raise e

COOKER_APP_API_KEY = response["Parameter"]["Value"]
COOKER_APP_ORIGIN = "cooker"


try:
    response = ssm_client.get_parameter(
        Name=os.getenv("AWS_API_KEY_CUSTOMER_APP"), WithDecryption=False
    )
except ClientError as e:
    raise e

CUSTOMER_APP_API_KEY = response["Parameter"]["Value"]
CUSTOMER_APP_ORIGIN = "customer"

try:
    response = ssm_client.get_parameter(
        Name=os.getenv("AWS_API_KEY_DELIVERY_APP"), WithDecryption=False
    )
except ClientError as e:
    raise e

DELIVERY_APP_API_KEY = response["Parameter"]["Value"]
DELIVERY_APP_ORIGIN = "delivery"


try:
    response = ssm_client.get_parameter(
        Name=os.getenv("GOOGLE_API_KEY"), WithDecryption=False
    )
except ClientError as e:
    raise e

GOOGLE_API_KEY = response["Parameter"]["Value"]

try:
    response = ssm_client.get_parameter(
        Name=os.getenv("AWS_API_KEY_STRIPE_PRIVATE"), WithDecryption=False
    )
except ClientError as e:
    raise e

STRIPE_PRIVATE_API_KEY = response["Parameter"]["Value"]

try:
    response = ssm_client.get_parameter(
        Name=os.getenv("AWS_API_KEY_STRIPE_WEBHOOK_ENDPOINT_SIGNATURE"),
        WithDecryption=False,
    )
except ClientError as e:
    raise e

STRIPE_WEBHOOK_ENDPOINT_SIGNATURE = response["Parameter"]["Value"]

DEFAULT_SEARCH_COUNTRY = "France"

DEFAULT_SEARCH_RADIUS = 2  # in KM

IDLE_CANCEL_TIME_FOR_ASAP_DELIVERY = 5  # in minutes
IDLE_CANCEL_TIME_FOR_SCHEDULED_DELIVERY = 60  # in minutes

SIMPLE_JWT = {
    "ALGORITHM": os.getenv("DJANGO_SIMPLE_JWT_ALGORITHM"),
    "SIGNING_KEY": secret_key,
    "VERIFYING_KEY": verifying_key,
    "TOKEN_OBTAIN_SERIALIZER": "cookers_app.serializers.TokenObtainPairWithoutPasswordSerializer",
}

propagate = True
handlers = ["watchtower"]
SERVICE_FEES_RATE = 0.07
DEFAULT_CURRENCY = "EUR"

ACCEPTANCE_RATE_INCREASE_VALUE = 2
ACCEPTANCE_RATE_DECREASE_VALUE = 10

if os.getenv("ENV") == "local":
    propagate = False
    handlers = ["console"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "aws": {
            # you can add specific format for aws here
            # if you want to change format, you can read:
            #    https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python/44401529
            "format": "%(asctime)s [%(levelname)-8s] %(message)s [%(pathname)s:%(lineno)d]",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "root": {
        "level": "INFO",
        # Adding the watchtower handler here causes all loggers in the project that
        # have propagate=True (the default) to send messages to watchtower. If you
        # wish to send only from specific loggers instead, remove "watchtower" here
        # and configure individual loggers below.
        "handlers": handlers,
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "aws",
            "level": "DEBUG",
        },
        "watchtower": {
            "class": "watchtower.CloudWatchLogHandler",
            "boto3_client": boto3_logs_client,
            "log_group_name": os.getenv("AWS_LOG_GROUP_NAME"),
            # Decrease the verbosity level here to send only those logs to watchtower,
            # but still see more verbose logs in the console. See the watchtower
            # documentation for other parameters that can be set here.
            "level": "INFO",
            "formatter": "aws",
        },
    },
    "loggers": {
        # In the debug server (`manage.py runserver`), several Django system loggers cause
        # deadlocks when using threading in the logging handler, and are not supported by
        # watchtower. This limitation does not apply when running on production WSGI servers
        # (gunicorn, uwsgi, etc.), so we recommend that you set `propagate=True` below in your
        # production-specific Django settings file to receive Django system logs in CloudWatch.
        "reats_logger": {
            "level": "INFO",
            "handlers": handlers,
            "propagate": propagate,
        }
        # Add any other logger-specific configuration here.
    },
}
