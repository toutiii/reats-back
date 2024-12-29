import pytest
from core_app.models import DishModel
from rest_framework import status
from rest_framework.test import APIClient


class TestListStartersForCustomerSuccess:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 4

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_starter_path: str,
    ) -> None:

        # we check that the cooker has some starters
        assert (
            DishModel.objects.filter(category="starter")
            .filter(cooker__id=cooker_id)
            .filter(is_enabled=True)
            .count()
            > 0
        )

        # Then we list the starters
        response = client.get(
            f"{customer_starter_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "data": [
                {
                    "category": "starter",
                    "cooker": "4",
                    "country": "Cameroun",
                    "description": "Test",
                    "id": "1",
                    "is_enabled": True,
                    "name": "Beignets haricots",
                    "photo": "https://some-url.com",
                    "price": "10.0",
                    "is_suitable_for_quick_delivery": False,
                    "is_suitable_for_scheduled_delivery": False,
                }
            ],
            "ok": True,
            "status_code": 200,
        }


class TestListStartersForCustomeFailedWithUnknownCookerId:
    @pytest.fixture
    def cooker_id(self) -> int:
        return 99

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        customer_starter_path: str,
    ) -> None:

        # we assert that no starter is linked to the unknown cooker
        assert DishModel.objects.filter(cooker__id=cooker_id).count() == 0

        # Then we try to list the starters
        response = client.get(
            f"{customer_starter_path}?cooker_id={cooker_id}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}


class TestListStartersForCustomerFailedWithoutCookerId:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_starter_path: str,
    ) -> None:

        # Then we list the starters without specifying the cooker_id
        response = client.get(
            customer_starter_path,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}
