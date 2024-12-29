import pytest
from core_app.models import DishModel
from deepdiff import DeepDiff
from rest_framework import status
from rest_framework.test import APIClient


class TestListDessertsForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 1

    @pytest.fixture
    def expected_data(self) -> list[dict]:
        return [
            {
                "id": "11",
                "category": "dessert",
                "country": "Italie",
                "description": "Tiramisu maison au spéculos",
                "name": "Tiramisu spéculos",
                "price": "5.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "12",
                "category": "dessert",
                "country": "France",
                "description": "Crème catalane",
                "name": "Crème catalane",
                "price": "6.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "13",
                "category": "dessert",
                "country": "France",
                "description": "Gateau moelleux au chocolat",
                "name": "part de gâteau au chocolat",
                "price": "2.5",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "14",
                "category": "dessert",
                "country": "France",
                "description": "Recette maison de pain perdu au lait",
                "name": "pain perdu",
                "price": "2.5",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "15",
                "category": "dessert",
                "country": "France",
                "description": "Cupcakes vanille vendu par 6",
                "name": "Cupcakes vanille",
                "price": "5.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
        ]

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_dessert_path: str,
        expected_data: list[dict],
    ) -> None:

        # we check that the cooker has some desserts
        assert (
            DishModel.objects.filter(category="dessert")
            .filter(cooker__id=cooker_id)
            .filter(is_enabled=True)
            .count()
            > 0
        )

        # Then we list the desserts
        response = client.get(
            f"{customer_dessert_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("ok") is True
        assert response.json().get("status_code") == status.HTTP_200_OK

        diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

        assert not diff


class TestListDessertsForCustomeFailedWithUnknownCookerId:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 99

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_dessert_path: str,
    ) -> None:

        # we assert that no dessert is linked to the unknown cooker
        assert DishModel.objects.filter(cooker__id=cooker_id).count() == 0

        # Then we try to list the desserts
        response = client.get(
            f"{customer_dessert_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}


class TestListDessertsForCustomerFailedWithoutCookerId:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dessert_path: str,
    ) -> None:

        # Then we list the desserts without specifying the cooker_id
        response = client.get(
            customer_dessert_path,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}
