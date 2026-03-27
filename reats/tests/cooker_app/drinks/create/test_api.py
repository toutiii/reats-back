import json
from unittest.mock import MagicMock

import pytest
from core_app.models import DrinkModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def ingredients() -> list[dict]:
    return [{"code": "sucre", "name": "Sucre", "is_allergen": False}]


@pytest.fixture
def post_data(image: InMemoryUploadedFile, ingredients: list[dict]) -> dict:
    return {
        "unit": "liter",
        "country": "Sénégal",
        "description": "Bissap maison",
        "name": "Bissap",
        "price": "3.5",
        "photos": [image],
        "cooker": 1,
        "capacity": "1",
        "ingredients": json.dumps(ingredients),
    }


@pytest.mark.django_db
class TestCreateDrinkSuccess:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        post_data: dict,
        ingredients: list[dict],
        upload_fileobj: MagicMock,
    ) -> None:
        pre_create_count = DrinkModel.objects.count()

        response = client.post(
            path, encode_multipart(BOUNDARY, post_data), content_type=MULTIPART_CONTENT, follow=False, **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        drink = DrinkModel.objects.latest("pk")
        assert drink.images.count() == 1  # type: ignore
        assert drink.images.first().key == "cookers/1/drinks/test.jpg"  # type: ignore

        assert drink.ingredients.count() == 1
        ingredient = drink.ingredients.first()
        assert ingredient.code == ingredients[0]["code"]  # type: ignore[union-attr]
        assert ingredient.is_allergen == ingredients[0]["is_allergen"]  # type: ignore[union-attr]

        response_ingredients = response.json()["data"]["ingredients"]
        assert len(response_ingredients) == 1
        assert response_ingredients[0]["code"] == ingredients[0]["code"]
        assert response_ingredients[0]["is_allergen"] == ingredients[0]["is_allergen"]

        upload_fileobj.assert_called_once()
        post_create_count = DrinkModel.objects.count()

        assert post_create_count - pre_create_count == 1
        assert len(upload_fileobj.call_args.args) == 3

        arg1, arg2, arg3 = upload_fileobj.call_args.args

        assert isinstance(arg1, InMemoryUploadedFile)
        assert arg1.name == "test.jpg"
        assert arg2 == "reats-dev-bucket"
        assert arg3 == "cookers/1/drinks/test.jpg"
