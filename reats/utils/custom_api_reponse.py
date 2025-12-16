from datetime import datetime, timezone
from typing import Any

from rest_framework import status
from rest_framework.response import Response


class CustomApiResponse:
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = status.HTTP_200_OK,
        extra_data: dict | None = None,
    ) -> Response:
        payload: dict = {
            "success": True,
            "data": data or {},
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if extra_data:
            payload.update(extra_data)
        return Response(payload, status=status_code)

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
    ):
        return CustomApiResponse.success(data, message, status_code, extra)

    def error(
        self,
        message,
        code="INTERNAL_SERVER_ERROR",
        details=None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        extra=None,
    ):
        return CustomApiResponse.error(message, code, details, status_code, extra)