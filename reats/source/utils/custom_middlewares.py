import logging
from http import HTTPStatus
from pprint import pformat

from rest_framework.views import exception_handler

logger = logging.getLogger(__file__)


def custom_exception_handler(exc, context):
    # Get standard error response from REST framework's default exception handler:
    response = exception_handler(exc, context)

    if response is not None and response.status_code == HTTPStatus.BAD_REQUEST:
        # Log response data for bad request to simplify debugging:
        logger.warning(f"Bad request to {context['request'].path}: {response.data}")
        logger.warning(pformat(context["request"].__dict__))

    return response
