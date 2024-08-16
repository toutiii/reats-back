import pytest
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_get_dishes_countries(
    auth_headers: dict,
    client: APIClient,
    customer_dishes_countries_path: str,
):
    response = client.get(
        f"{customer_dishes_countries_path}",
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "ok": True,
        "status_code": 200,
        "data": [
            "Benin",
            "Cameroun",
            "Congo",
            "Nigeria",
        ],
    }


@pytest.mark.django_db
class TestGetDishesCountriesFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000001"}

    def test_response(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        customer_dishes_countries_path: str,
    ) -> None:

        with freeze_time("2024-01-20T17:05:45+00:00"):
            token_response = client.post(
                "/api/v1/token/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **customer_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:30:45+00:00"):
            response = client.delete(
                f"{customer_dishes_countries_path}",
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error_code") == "token_not_valid"
