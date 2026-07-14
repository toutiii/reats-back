from unittest.mock import MagicMock

import pytest
from core_app.models import CustomerModel
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum, ErrorMessageEnum, SuccessMessageEnum


@pytest.mark.django_db
class TestCustomerDeleteSuccess:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000001"}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        data: dict,
        path: str,
        mock_stripe_customer_delete: MagicMock,
    ) -> None:
        customer_id = 1

        with freeze_time("2024-01-20T17:05:45+00:00"):
            response = client.delete(
                f"{path}{customer_id}/",
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json().get("success") is True
            assert response.json().get("message") == SuccessMessageEnum.ACCOUNT_DELETED

            assert CustomerModel.objects.get(phone=data.get("phone")).is_deleted is True
            assert CustomerModel.objects.get(pk=customer_id).is_deleted is True

            mock_stripe_customer_delete.assert_called_once_with("cus_QyZ76Ae0W5KeqP")


@pytest.mark.django_db
class TestCustomerDeleteFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000003"}

    def test_response(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        path: str,
        customer_access_token,
        mock_stripe_customer_delete: MagicMock,
    ) -> None:
        customer_id = 3

        with freeze_time("2024-01-20T17:05:45+00:00"):
            # On part d'un token fraîchement émis, comme au sortir d'une validation d'OTP
            access_token = customer_access_token(data["phone"])
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        # Then we skip 15 minutes in the future to make the token expired
        with freeze_time("2024-01-20T17:15:45+00:00"):
            response = client.delete(
                f"{path}{customer_id}/",
                follow=False,
                **access_auth_header,
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("success") is False
            assert response.json().get("error").get("message") == ErrorMessageEnum.TOKEN_NOT_VALID
            assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID

            mock_stripe_customer_delete.assert_not_called()


@pytest.mark.django_db
class TestCustomerDeleteUnknownId:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        mock_stripe_customer_delete: MagicMock,
    ) -> None:
        customer_id = 999

        with freeze_time("2024-01-20T17:05:45+00:00"):
            response = client.delete(
                f"{path}{customer_id}/",
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json().get("success") is False
            assert response.json().get("error").get("message") == ErrorMessageEnum.NOT_FOUND
            assert response.json().get("error").get("code") == ErrorCodeEnum.NOT_FOUND

            mock_stripe_customer_delete.assert_not_called()
