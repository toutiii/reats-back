import pytest
from cooker_app.models import DrinkModel
from rest_framework import status
from rest_framework.test import APIClient


class TestListDrinksForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 1

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_drink_path: str,
    ) -> None:

        # we check that the cooker has some drinks
        assert (
            DrinkModel.objects.filter(cooker__id=cooker_id)
            .filter(is_enabled=True)
            .count()
            > 0
        )

        # Then we list the drinks
        response = client.get(
            f"{customer_drink_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "data": [
                {
                    "capacity": "1",
                    "cooker": "1",
                    "country": "Sénégal",
                    "description": "Bissap maison",
                    "id": "1",
                    "is_enabled": True,
                    "name": "Bissap",
                    "photo": "https://some-url.com",
                    "price": "3.5",
                    "unit": "liter",
                },
                {
                    "capacity": "75",
                    "cooker": "1",
                    "country": "Cameroun",
                    "description": "Gingembre maison",
                    "id": "2",
                    "is_enabled": True,
                    "name": "Gingembre",
                    "photo": "https://some-url.com",
                    "price": "5.0",
                    "unit": "centiliters",
                },
            ],
            "ok": True,
            "status_code": 200,
        }


class TestListDrinksForCustomeFailedWithUnknownCookerId:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 99

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_drink_path: str,
    ) -> None:

        # we assert that no drinks are associated with the cooker
        assert DrinkModel.objects.filter(cooker__id=cooker_id).count() == 0

        # Then we try to list the drinks
        response = client.get(
            f"{customer_drink_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}


class TestListDrinksForCustomerFailedWithoutCookerId:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_drink_path: str,
    ) -> None:

        # Then we list the drinks without
        response = client.get(
            customer_drink_path,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}
