from typing import Any, Callable

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from utils.enums import ErrorCodeEnum, ErrorMessageEnum, SuccessMessageEnum


class ExceptionHandler:
    def __init__(self):
        self._handlers = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.register(
            (TokenError, InvalidToken, AuthenticationFailed),
            {
                "message": ErrorMessageEnum.TOKEN_NOT_VALID,
                "code": ErrorCodeEnum.TOKEN_NOT_VALID,
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.register(
            ValidationError,
            {
                "message": ErrorMessageEnum.VALIDATION_FAILED,
                "code": ErrorCodeEnum.VALIDATION_ERROR,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "extract_details": True,
            },
        )
        self.register(
            PermissionDenied,
            {
                "message": ErrorMessageEnum.PERMISSION_DENIED,
                "code": ErrorCodeEnum.PERMISSION_DENIED,
                "status_code": status.HTTP_403_FORBIDDEN,
                "extract_details": True,
            },
        )
        self.register(
            NotFound,
            {
                "message": ErrorMessageEnum.NOT_FOUND,
                "code": ErrorCodeEnum.NOT_FOUND,
                "status_code": status.HTTP_404_NOT_FOUND,
                "extract_details": True,
            },
        )

    def register(self, exc_type, handler_config: dict):
        if isinstance(exc_type, tuple):
            for exc_class in exc_type:
                self._handlers[exc_class] = handler_config
        else:
            self._handlers[exc_type] = handler_config

    def get_handler_config(self, exc: Exception) -> dict | None:
        for exc_type, config in self._handlers.items():
            if isinstance(exc, exc_type):
                return config
        return None

    def build_error_response(self, exc: Exception, error_method: Callable) -> Response | None:
        config = self.get_handler_config(exc)
        if not config:
            return None

        details = None
        if config.get("extract_details"):
            details = getattr(exc, "detail", {})

        return error_method(
            message=config["message"],
            code=config["code"],
            status_code=config["status_code"],
            details=details,
        )


exception_handler = ExceptionHandler()


class CustomApiResponse:
    @staticmethod
    def success(
        data: Any = None,
        message: str = SuccessMessageEnum.OPERATION_SUCCESSFUL,
        status_code: int = status.HTTP_200_OK,
        extra_data: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if isinstance(data, dict) and {"success", "data", "message"}.issubset(data.keys()):
            return Response(data, status=status_code, headers=headers)

        payload: dict = {
            "success": True,
            "data": data if data is not None else {},
            "message": message,
        }
        if extra_data:
            payload.update(extra_data)
        return Response(payload, status=status_code, headers=headers)

    @staticmethod
    def error(
        message: str = "Operation failed",
        code: str = ErrorCodeEnum.INTERNAL_SERVER_ERROR,
        details: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        extra_data: dict | None = None,
    ) -> Response:
        payload: dict = {
            "success": False,
            "error": {"code": code, "message": message, "details": details or {}},
        }
        if extra_data:
            payload.update(extra_data)
        return Response(payload, status=status_code)


class StandardizedResponseMixin:
    def success(
        self,
        data=None,
        message=SuccessMessageEnum.OPERATION_SUCCESSFUL,
        status_code=status.HTTP_200_OK,
        extra=None,
        headers=None,
    ):
        return CustomApiResponse.success(data, message, status_code, extra, headers)

    def error(
        self,
        message,
        code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
        details=None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        extra=None,
    ):
        return CustomApiResponse.error(message, code, details, status_code, extra)

    def handle_exception(self, exc):
        try:
            response = super().handle_exception(exc)  # ty: ignore[unresolved-attribute]
        except (TokenError, InvalidToken):
            return self.error(
                message=ErrorMessageEnum.TOKEN_NOT_VALID,
                code=ErrorCodeEnum.TOKEN_NOT_VALID,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if response is None:
            handler_response = exception_handler.build_error_response(exc, self.error)
            if handler_response:
                return handler_response

            return self.error(
                message=str(exc) or "Operation failed",
                code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
                details=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return self._process_existing_response(response)

    def _process_existing_response(self, response: Response) -> Response:
        resp_data = getattr(response, "data", None)
        if resp_data is None:
            return response

        if isinstance(resp_data, dict) and "success" in resp_data:
            return response

        message = "Operation failed"
        code = "API_ERROR"
        details = resp_data

        if isinstance(details, dict) and "detail" in details:
            detail_obj = details["detail"]
            if getattr(detail_obj, "code", None):
                code = detail_obj.code
            message = str(detail_obj)
            if message == "Given token not valid for any token type":
                message = ErrorMessageEnum.TOKEN_NOT_VALID

        if response.status_code == status.HTTP_404_NOT_FOUND:
            code = ErrorCodeEnum.NOT_FOUND
            message = ErrorMessageEnum.NOT_FOUND

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            code = ErrorCodeEnum.VALIDATION_ERROR
            message = ErrorMessageEnum.VALIDATION_FAILED

        return self.error(
            message=message,
            code=code,
            details=details,
            status_code=response.status_code,
        )
