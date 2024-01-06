from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication


class UserPermission(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        JWT_authenticator = JWTAuthentication()
        response = JWT_authenticator.authenticate(request)
        print(request)
        print(response)

        if request.user and response:
            print(f"Permission granted for user {request.user}")
            return True
        print(f"Permission denied for user {request.user}")
        return False
