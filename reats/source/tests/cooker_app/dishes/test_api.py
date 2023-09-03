import pytest
from rest_framework import status
from rest_framework.test import APIClient
from source.cooker_app.models import DishModel


@pytest.fixture
def path() -> str:
    return "/api/v1/dishes/"


@pytest.fixture
def post_data(category: str) -> dict:
    return {
        "category": category,
        "cooker": 1,
        "country": "Cameroun",
        "description": "Test",
        "name": "Beignets haricots",
        "photo": "s3://some-link-to-aws-s3-buket-some-dish-picture.jpeg",
        "price": "10",
    }


@pytest.mark.django_db
class TestCreateDishSuccess:
    @pytest.fixture(params=["starter", "main_dish", "dessert"])
    def category(self, request) -> str:
        return request.param

    def test_response(
        self,
        client: APIClient,
        path: str,
        post_data: dict,
    ) -> None:
        response = client.post(path, post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert DishModel.objects.count() == 1


@pytest.mark.django_db
class TestCreateDishFailedInvalidCategory:
    @pytest.fixture
    def category(self) -> str:
        return "invalid_category"

    def test_response(
        self,
        client: APIClient,
        path: str,
        post_data: dict,
    ) -> None:
        response = client.post(path, post_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DishModel.objects.count() == 0
