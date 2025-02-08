from unittest.mock import ANY, MagicMock

import pytest
from core_app.models import CustomerModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


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
            {"phone": "0700000007"},
            {"phone": "0700000004"},
        ],
        ids=[
            "missing_phone_number",
            "invalid_phone_number",
            "unknown_user",
            "known_but_non_activated_user",
        ],
    )
    @pytest.mark.django_db
    def test_customer_auth_failed(
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


class TestTokenFetch:
    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"unexpected_field": "test_data"},
            {"username": "test", "password": "test"},
        ],
        ids=[
            "missing_field",
            "invalid_field",
            "deprecated_fields",
        ],
    )
    def test_fetch_token_failed_with_missing_phone_field(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        token_path: str,
        secrets_manager_get_secret: MagicMock,
    ) -> None:
        response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        secrets_manager_get_secret.assert_not_called()

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "0700000003"}

    @pytest.mark.django_db
    def test_fetch_token_success(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        token_path: str,
        secrets_manager_get_secret: MagicMock,
    ) -> None:
        response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
            "token": {
                "access": ANY,
                "refresh": ANY,
            },
            "user_id": ANY,
        }
        secrets_manager_get_secret.assert_not_called()


class TestTokenFetchWhenUserIsPresentOnMultipleTables:
    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "+33700000006"}

    @pytest.mark.django_db
    def test_fetch_token_success(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        token_path: str,
        secrets_manager_get_secret: MagicMock,
    ) -> None:
        response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
            "token": {
                "access": ANY,
                "refresh": ANY,
            },
            "user_id": ANY,
        }
        secrets_manager_get_secret.assert_not_called()
        assert (
            response.json()["user_id"]
            == CustomerModel.objects.get(phone="+33700000006").pk
        )
