import pytest
from core_app.models import DrinkModel
from deepdiff import DeepDiff
from rest_framework import status
from rest_framework.test import APIClient


class TestListDrinksForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 1

    @pytest.fixture
    def expected_data(self) -> list[dict]:
        return [
            {
                "capacity": "1",
                "cooker": {
                    "acceptance_rate": 100.0,
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                },
                "country": "Sénégal",
                "description": "Bissap maison",
                "id": "1",
                "is_enabled": True,
                "name": "Bissap",
                "photo": "https://some-url.com",
                "price": "3.5",
                "unit": "liter",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "ratings": "[]",
            },
            {
                "capacity": "75",
                "cooker": {
                    "acceptance_rate": 100.0,
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                },
                "country": "Cameroun",
                "description": "Gingembre maison",
                "id": "2",
                "is_enabled": True,
                "name": "Gingembre",
                "photo": "https://some-url.com",
                "price": "5.0",
                "unit": "centiliters",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "ratings": "[]",
            },
        ]

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_drink_path: str,
        expected_data: list[dict],
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
        assert response.json().get("ok") is True
        assert response.json().get("status_code") == status.HTTP_200_OK
        diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)
        assert not diff


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
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
            "data": [],
        }


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
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
            "data": [],
        }
