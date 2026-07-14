from unittest.mock import ANY, MagicMock

import pytest
from core_app.models import CustomerModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum


class TestCustomerAuth:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33700000003"

    @pytest.fixture
    def auth_data(self) -> dict:
        return {"phone": "0700000003"}

    @pytest.mark.parametrize(
        "auth_data",
        [
            {},
            {"phone": "this_is_not_a_phone_number"},
        ],
        ids=[
            "missing_phone_number",
            "invalid_phone_number",
        ],
    )
    @pytest.mark.django_db
    def test_customer_auth_failed_bad_request(
        self,
        customer_api_key_header: dict,
        auth_data: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, auth_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_customer_auth_failed_not_found(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, {"phone": "0700000007"}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_customer_auth_failed_forbidden(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, {"phone": "0700000004"}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_customer_auth_success(
        self,
        customer_api_key_header: dict,
        auth_data: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, auth_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )
        assert response.status_code == status.HTTP_200_OK
        send_otp_message_success.assert_called_once_with(
            ApplicationId=ANY,
            SendOTPMessageRequestParameters={
                "Channel": "SMS",
                "BrandName": ANY,
                "CodeLength": 6,
                "ValidityPeriod": 30,
                "AllowedAttempts": 3,
                "Language": "fr-FR",
                "OriginationIdentity": ANY,
                "DestinationIdentity": "+33700000003",
                "ReferenceId": ANY,
            },
        )


class TestCustomerAskNewOTP:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33700000003"

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "0700000003"}

    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"phone": "this_is_not_a_phone_number"},
            {"phone": "0700000007"},
        ],
        ids=[
            "missing_phone_number",
            "invalid_phone_number",
            "unknown_user",
        ],
    )
    @pytest.mark.django_db
    def test_customer_ask_new_OTP_failed(
        self,
        customer_api_key_header: dict,
        data: dict,
        client: APIClient,
        otp_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_customer_ask_new_OTP_success(
        self,
        customer_api_key_header: dict,
        data: dict,
        client: APIClient,
        otp_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_200_OK
        send_otp_message_success.assert_called_once_with(
            ApplicationId=ANY,
            SendOTPMessageRequestParameters={
                "Channel": "SMS",
                "BrandName": ANY,
                "CodeLength": 6,
                "ValidityPeriod": 30,
                "AllowedAttempts": 3,
                "Language": "fr-FR",
                "OriginationIdentity": ANY,
                "DestinationIdentity": "+33700000003",
                "ReferenceId": ANY,
            },
        )


@pytest.mark.django_db
class TestTokenIssuanceIsBoundToOTP:
    """L'émission d'un token est adossée à la validation de l'OTP, et à rien d'autre.

    Il n'existe plus de route qui délivre une paire sur simple présentation d'un numéro :
    la clé d'API voyage dans le bundle des apps, donc elle est publique — un tel endpoint
    authentifierait n'importe qui.
    """

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "0700000003", "otp": "111111"}

    def test_token_obtain_route_no_longer_exists(
        self,
        customer_api_key_header: dict,
        client: APIClient,
    ) -> None:
        response = client.post(
            "/api/v1/token/",
            encode_multipart(BOUNDARY, {"phone": "0700000003"}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_otp_verify_returns_a_token_pair(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        otp_verify_path: str,
        verify_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        assert response.json().get("message") == SuccessMessageEnum.ACCOUNT_ACTIVATED
        assert response.json().get("data").get("token").get("access") is not None
        assert response.json().get("data").get("token").get("refresh") is not None
        assert response.json().get("data").get("user_id") == CustomerModel.objects.get(phone="+33700000003").pk

    def test_otp_verify_issues_no_token_when_the_code_is_wrong(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        otp_verify_path: str,
        verify_otp_message_failed: MagicMock,
    ) -> None:
        response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json().get("success") is False
        assert "token" not in (response.json().get("data") or {})


@pytest.mark.django_db
class TestTokenIssuanceWhenUserIsPresentOnMultipleTables:
    """Un même numéro peut exister dans les trois tables : chaque app a son endpoint, donc
    le bon utilisateur est choisi par construction, sans dépendre d'un en-tête falsifiable."""

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "+33700000006", "otp": "111111"}

    def test_otp_verify_returns_the_customer_of_that_phone(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        otp_verify_path: str,
        verify_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("data").get("token").get("access") is not None
        assert response.json().get("data").get("user_id") == CustomerModel.objects.get(phone="+33700000006").pk
