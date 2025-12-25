from typing import Any

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


class CustomApiResponse:
    @staticmethod
    def success(
        data: Any = None,
        message: str = SuccessMessageEnum.OPERATION_SUCCESSFUL,
        status_code: int = status.HTTP_200_OK,
        extra_data: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
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
            response = super().handle_exception(exc)
        except (TokenError, InvalidToken):
            return self.error(
                message=ErrorMessageEnum.TOKEN_NOT_VALID,
                code=ErrorCodeEnum.TOKEN_NOT_VALID,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Si super() ne renvoie pas de Response, je dois construire une réponse standardisée
        if response is None:
            if isinstance(exc, (TokenError, InvalidToken, AuthenticationFailed)):
                return self.error(
                    message=ErrorMessageEnum.TOKEN_NOT_VALID,
                    code=ErrorCodeEnum.TOKEN_NOT_VALID,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            if isinstance(exc, ValidationError):
                return self.error(
                    message=ErrorMessageEnum.VALIDATION_FAILED,
                    code=ErrorCodeEnum.VALIDATION_ERROR,
                    details=getattr(exc, "detail", {}),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if isinstance(exc, PermissionDenied):
                return self.error(
                    message=ErrorMessageEnum.PERMISSION_DENIED,
                    code=ErrorCodeEnum.PERMISSION_DENIED,
                    details=getattr(exc, "detail", {}),
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            if isinstance(exc, NotFound):
                return self.error(
                    message=ErrorMessageEnum.NOT_FOUND,
                    code=ErrorCodeEnum.NOT_FOUND,
                    details=getattr(exc, "detail", {}),
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            # Dans la mesure ou les exceptions non gérées arrivent ici, on renvoie une erreur 500
            return self.error(
                message=str(exc) or "Operation failed",
                code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
                details=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Si response existe, garder la logique existante.
        resp_data = getattr(response, "data", None)
        if resp_data is not None:
            if isinstance(resp_data, dict) and "success" in resp_data:
                return response

            message = "Operation failed"
            code = "API_ERROR"
            details = resp_data

            if isinstance(details, dict):
                if "detail" in details:
                    detail_obj = details["detail"]
                    if getattr(detail_obj, "code", None):
                        code = detail_obj.code
                    message = str(detail_obj)
                    if message == "Given token not valid for any token type":
                        message = ErrorMessageEnum.TOKEN_NOT_VALID

                if response.status_code == status.HTTP_400_BAD_REQUEST:
                    code = ErrorCodeEnum.VALIDATION_ERROR
                    message = ErrorMessageEnum.VALIDATION_FAILED

            return self.error(
                message=message,
                code=code,
                details=details,
                status_code=response.status_code,
            )

        return response
