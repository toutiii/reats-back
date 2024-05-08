import pytest
from cooker_app.models import DishModel
from rest_framework import status
from rest_framework.test import APIClient


class TestListDessertsForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 1

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_dessert_path: str,
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
        assert response.json() == {
            "data": [
                {
                    "category": "dessert",
                    "cooker": "1",
                    "country": "Italie",
                    "description": "Tiramisu maison au spéculos",
                    "id": "11",
                    "is_enabled": True,
                    "name": "Tiramisu spéculos",
                    "photo": "https://some-url.com",
                    "price": "5.0",
                },
                {
                    "category": "dessert",
                    "cooker": "1",
                    "country": "France",
                    "description": "Crème catalane",
                    "id": "12",
                    "is_enabled": True,
                    "name": "Crème catalane",
                    "photo": "https://some-url.com",
                    "price": "6.0",
                },
                {
                    "category": "dessert",
                    "cooker": "1",
                    "country": "France",
                    "description": "Gateau moelleux au chocolat",
                    "id": "13",
                    "is_enabled": True,
                    "name": "part de gâteau au chocolat",
                    "photo": "https://some-url.com",
                    "price": "2.5",
                },
                {
                    "category": "dessert",
                    "cooker": "1",
                    "country": "France",
                    "description": "Recette maison de pain perdu au lait",
                    "id": "14",
                    "is_enabled": True,
                    "name": "pain perdu",
                    "photo": "https://some-url.com",
                    "price": "2.5",
                },
                {
                    "category": "dessert",
                    "cooker": "1",
                    "country": "France",
                    "description": "Cupcakes vanille vendu par 6",
                    "id": "15",
                    "is_enabled": True,
                    "name": "Cupcakes vanille",
                    "photo": "https://some-url.com",
                    "price": "5.0",
                },
            ],
            "ok": True,
            "status_code": 200,
        }


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
