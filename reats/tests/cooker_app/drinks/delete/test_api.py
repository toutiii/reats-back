import pytest
from core_app.models import DrinkModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def drink_id() -> int:
    return 2


@pytest.mark.django_db
class TestDrinkDeleteSuccess:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        drink_id: int,
        path: str,
    ):
        response = client.delete(
            f"{path}{drink_id}/",
            encode_multipart(BOUNDARY, {}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
        }

        assert DrinkModel.objects.get(pk=drink_id).is_deleted is True


@pytest.mark.django_db
class TestDrinkDeleteFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33766964170"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        data: dict,
        drink_id: int,
        path: str,
        token_path: str,
    ) -> None:

        with freeze_time("2024-01-20T17:05:45+00:00"):
            token_response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:30:45+00:00"):
            response = client.delete(
                f"{path}{drink_id}/",
                encode_multipart(BOUNDARY, {}),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error_code") == "token_not_valid"


@pytest.mark.django_db
def test_get_enabled_drinks_when_item_has_been_deleted(
    auth_headers: dict,
    client: APIClient,
    path: str,
) -> None:
    cooker_id: int = 1
    first_drink = DrinkModel.objects.filter(cooker__id=cooker_id).first()

    if first_drink is not None:
        first_drink.is_deleted = True
        first_drink.save()
    else:
        assert False

    response = client.get(
        path,
        {"is_enabled": "true"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is True
        assert DrinkModel.objects.get(pk=item.get("id")).is_deleted is False
