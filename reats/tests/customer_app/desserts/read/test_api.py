import pytest
from core_app.models import DishModel
from deepdiff import DeepDiff
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum


class TestListDessertsForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 1

    @pytest.fixture
    def expected_data(self) -> list[dict]:
        return [
            {
                "id": 13,
                "ratings": [],
                "category": "dessert",
                "country": "France",
                "description": "Gateau moelleux au chocolat",
                "name": "part de gâteau au chocolat",
                "price": 2.5,
                "image": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "email": "test@gmail.com",
                    "acceptance_rate": 100.0,
                },
                "allergens": [],
                "ingredients": [],
            },
            {
                "id": 14,
                "ratings": [],
                "category": "dessert",
                "country": "France",
                "description": "Recette maison de pain perdu au lait",
                "name": "pain perdu",
                "price": 2.5,
                "image": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "email": "test@gmail.com",
                    "acceptance_rate": 100.0,
                },
                "allergens": [],
                "ingredients": [],
            },
            {
                "id": 15,
                "ratings": [],
                "category": "dessert",
                "country": "France",
                "description": "Cupcakes vanille vendu par 6",
                "name": "Cupcakes vanille",
                "price": 5.0,
                "image": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "email": "test@gmail.com",
                    "acceptance_rate": 100.0,
                },
                "allergens": [],
                "ingredients": [],
            },
            {
                "id": 11,
                "ratings": [],
                "category": "dessert",
                "country": "Italie",
                "description": "Tiramisu maison au spéculos",
                "name": "Tiramisu spéculos",
                "price": 5.0,
                "image": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "email": "test@gmail.com",
                    "acceptance_rate": 100.0,
                },
                "allergens": [],
                "ingredients": [],
            },
            {
                "id": 12,
                "ratings": [],
                "category": "dessert",
                "country": "France",
                "description": "Crème catalane",
                "name": "Crème catalane",
                "price": 6.0,
                "image": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "email": "test@gmail.com",
                    "acceptance_rate": 100.0,
                },
                "allergens": [],
                "ingredients": [],
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
            DishModel.objects.filter(category="dessert").filter(cooker__id=cooker_id).filter(is_enabled=True).count()
            > 0
        )

        # Then we list the desserts
        response = client.get(
            f"{customer_dessert_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        assert response.json().get("message") == SuccessMessageEnum.OPERATION_SUCCESSFUL.value

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
        assert response.json() == {
            "success": True,
            "message": SuccessMessageEnum.OPERATION_SUCCESSFUL.value,
            "data": [],
        }


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
        assert response.json() == {
            "success": True,
            "message": SuccessMessageEnum.OPERATION_SUCCESSFUL.value,
            "data": [],
        }


class TestListDessertsOnlyReturnNonDeletedItems:
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
        assert (
            DishModel.objects.filter(category="dessert").filter(cooker__id=cooker_id).filter(is_enabled=True).count()
            > 0
        )

        first_item = (
            DishModel.objects.filter(category="dessert").filter(cooker__id=cooker_id).filter(is_enabled=True).first()
        )
        if first_item is not None:
            first_item.is_deleted = True
            first_item.save()
        else:
            assert False

        response = client.get(
            f"{customer_dessert_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        assert response.json().get("message") == SuccessMessageEnum.OPERATION_SUCCESSFUL.value

        for item in response.json().get("data"):
            assert item.get("is_enabled") is True
            assert DishModel.objects.get(pk=int(item.get("id"))).is_deleted is False
