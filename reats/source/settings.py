"""
Django settings for reats project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

session = boto3.session.Session()

ssm_client = boto3.client("ssm", region_name=os.getenv("AWS_REGION"))
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ["DEBUG"]

SECRET_KEY = os.getenv("SECRET_KEY")


# Load all env vars in config/.env
load_dotenv(os.path.join(BASE_DIR, "config/.env"))

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
    "client_app",
    "cooker_app",
    "delivery_app",
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
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ["DB_PORT"],
    }
}


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


REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "utils.custom_middlewares.custom_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
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


SIMPLE_JWT = {
    "ALGORITHM": os.getenv("DJANGO_SIMPLE_JWT_ALGORITHM"),
    "SIGNING_KEY": secret_key,
    "VERIFYING_KEY": verifying_key,
    "TOKEN_OBTAIN_SERIALIZER": "cookers_app.serializers.TokenObtainPairWithoutPasswordSerializer",
}

AUTH_USER_MODEL = "cooker_app.GenericUser"
