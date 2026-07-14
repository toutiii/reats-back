from typing import Union, cast

from core_app.models import CookerModel, CustomerModel, DeliverModel
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, Token
from rest_framework_simplejwt.utils import datetime_from_epoch

AppUser = Union[CookerModel, CustomerModel, DeliverModel]


class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = Token.for_user.__func__(cls, user)

        if "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS:
            jti = token[api_settings.JTI_CLAIM]
            exp = token["exp"]

            OutstandingToken.objects.create(
                user=None,
                jti=jti,
                token=str(token),
                created_at=token.current_time,
                expires_at=datetime_from_epoch(exp),
            )

        return token


def issue_token_pair(user: AppUser) -> dict:
    """Émet une paire de tokens pour un utilisateur dont l'OTP vient d'être validé.

    Seul appelant légitime : l'action `otp_verify` des trois apps. L'émission d'un token
    reste ainsi adossée à une preuve de possession du numéro (le code reçu par SMS).
    Toute autre porte d'entrée reviendrait à authentifier sur simple présentation d'un
    numéro de téléphone, qui n'est pas un secret.
    """
    refresh = CustomRefreshToken.for_user(cast(AbstractBaseUser, user))

    return {
        "token": {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        },
        "user_id": user.pk,
    }
