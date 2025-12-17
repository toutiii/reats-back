from datetime import datetime, timezone
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import sys


class CustomApiResponse:
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = status.HTTP_200_OK,
        extra_data: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        payload: dict = {
            "success": True,
            "data": data if data is not None else {},
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if extra_data:
            payload.update(extra_data)
        return Response(payload, status=status_code, headers=headers)

    @staticmethod
    def error(
        message: str = "Operation failed",
        code: str = "INTERNAL_SERVER_ERROR",
        details: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        extra_data: dict | None = None,
    ) -> Response:
        payload: dict = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if extra_data:
            payload.update(extra_data)
        return Response(payload, status=status_code)


class StandardizedResponseMixin:
    def success(
        self,
        data=None,
        message="Operation successful",
        status_code=status.HTTP_200_OK,
        extra=None,
        headers=None,
    ):
        return CustomApiResponse.success(data, message, status_code, extra, headers)

    def error(
        self,
        message,
        code="INTERNAL_SERVER_ERROR",
        details=None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        extra=None,
    ):
        return CustomApiResponse.error(message, code, details, status_code, extra)

    def handle_exception(self, exc):
        try:
            response = super().handle_exception(exc)
        except (TokenError, InvalidToken):
             return self.error(
                message="Token is invalid or expired",
                code="token_not_valid",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        if response is None:
            if isinstance(exc, (TokenError, InvalidToken)):
                return self.error(
                    message="Token is invalid or expired",
                    code="token_not_valid",
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

        if response is not None:

            if isinstance(response.data, dict) and "success" in response.data:
                return response

            message = "Operation failed"
            code = "API_ERROR"
            details = response.data

            if isinstance(details, dict):
                if "detail" in details:
                    if getattr(details["detail"], "code", None):
                        code = details["detail"].code
                    message = str(details["detail"])
                    if message == "Given token not valid for any token type":
                        message = "Token is invalid or expired"

                if response.status_code == status.HTTP_400_BAD_REQUEST:
                    code = "VALIDATION_ERROR"
                    message = "Validation failed"

            error_response = self.error(
                message=message,
                code=code,
                details=details,
                status_code=response.status_code
            )
            return error_response

        return response