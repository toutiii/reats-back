import pytest
from core_app.models import CookerModel, DishModel, DrinkModel
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum


@pytest.mark.django_db
class TestCookerDeleteSuccess:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33766964170"}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        data: dict,
        path: str,
    ) -> None:
        cooker_id = 1

        response = client.delete(
            f"{path}{cooker_id}/",
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        assert CookerModel.objects.get(pk=cooker_id).is_deleted is True
        assert DishModel.objects.filter(cooker__id=cooker_id).count() > 0
        assert DrinkModel.objects.filter(cooker__id=cooker_id).count() > 0


@pytest.mark.django_db
class TestCookerDeleteFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33766964170"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        data: dict,
        path: str,
        cooker_access_token,
    ) -> None:
        cooker_id = 1

        with freeze_time("2024-01-20T17:05:45+00:00"):
            access_token = cooker_access_token(data["phone"])
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:30:45+00:00"):
            response = client.delete(
                f"{path}{cooker_id}/",
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("success") is False
            assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID
