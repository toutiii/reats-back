import pytest
from customer_app.models import CustomerModel
from django.core.exceptions import ObjectDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCustomerDeleteSuccess:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000003"}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        data: dict,
        path: str,
    ) -> None:
        customer_id = 3

        with freeze_time("2024-01-20T17:05:45+00:00"):
            response = client.delete(
                f"{path}{customer_id}/",
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }

            with pytest.raises(ObjectDoesNotExist):
                CustomerModel.objects.get(phone=data.get("phone"))

            with pytest.raises(ObjectDoesNotExist):
                CustomerModel.objects.get(pk=3)


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
        token_path: str,
    ) -> None:
        customer_id = 3

        with freeze_time("2024-01-20T17:05:45+00:00"):
            # First we ask a token as usual
            token_response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **customer_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:15:45+00:00"):
            response = client.delete(
                f"{path}{customer_id}/",
                follow=False,
                **access_auth_header,
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error_code") == "token_not_valid"
