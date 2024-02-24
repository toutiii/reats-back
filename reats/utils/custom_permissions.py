import logging

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

logger = logging.getLogger("watchtower-logger")

WHITE_LIST = [
    (settings.COOKER_APP_ORIGIN, settings.COOKER_APP_API_KEY),
    (settings.CUSTOMER_APP_ORIGIN, settings.CUSTOMER_APP_API_KEY),
]


class UserPermission(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        JWT_authenticator = JWTStatelessUserAuthentication()
        response = JWT_authenticator.authenticate(request)
        logger.info(request)
        logger.info(response)

        if request.user and response:
            logger.info(f"Permission granted for user {request.user}")
            return True
        logger.info(f"Permission denied for user {request.user}")
        return False


class CustomAPIKeyPermission(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        logger.info(request)
        logger.info(request.headers)
        app_origin = request.headers.get("App-Origin")
        api_key = request.headers.get("X-Api-Key")
        if api_key is None:
            return False

        if app_origin is None:
            return False

        if (app_origin, api_key) not in WHITE_LIST:
            return False

        return True
