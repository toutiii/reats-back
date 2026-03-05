from typing import IO, Any, cast
from unittest.mock import MagicMock

import pytest
from core_app.models import DrinkModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def post_data(image: InMemoryUploadedFile) -> dict:
    return {
        "unit": "liter",
        "country": "Sénégal",
        "description": "Bissap maison",
        "name": "Bissap",
        "price": "3.5",
        "photo": image,
        "cooker": 1,
        "capacity": "1",
    }


@pytest.mark.django_db
class TestCreateDrinkSuccess:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        post_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        pre_create_count = DrinkModel.objects.count()

        response = client.post(
            path, encode_multipart(BOUNDARY, post_data), content_type=MULTIPART_CONTENT, follow=False, **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert DrinkModel.objects.latest("pk").photo == "cookers/1/drinks/test.jpg"
        upload_fileobj.assert_called_once()
        post_create_count = DrinkModel.objects.count()

        assert post_create_count - pre_create_count == 1
        assert len(upload_fileobj.call_args.args) == 3

        arg1, arg2, arg3 = upload_fileobj.call_args.args

        assert isinstance(arg1, InMemoryUploadedFile)
        assert arg1.name == "test.jpg"
        assert arg2 == "reats-dev-bucket"
        assert arg3 == "cookers/1/drinks/test.jpg"


@pytest.fixture
def transparent_post_data(image: InMemoryUploadedFile) -> dict:
    import json

    return {
        "unit": "liter",
        "country": "Sénégal",
        "description": "Bissap maison transparent",
        "name": "Bissap Pro",
        "price": "5.0",
        "cost": "2.0",
        "photo": image,
        "cooker": 1,
        "capacity": "1",
        "allergens": ["GLU", "LAC"],
        "ingredients": ["SUG", "WAT"],
        "nutritional_info": json.dumps({"calories": 100, "protein": 1, "carbs": 25, "fat": 0}),
    }


@pytest.mark.django_db
class TestCreateTransparentDrinkSuccess:
    def test_transparency_fields(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        transparent_post_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        from core_app.models import AllergenModel, IngredientModel

        # Pre-requisite data
        AllergenModel.objects.get_or_create(code="GLU", defaults={"name": "Gluten"})
        AllergenModel.objects.get_or_create(code="LAC", defaults={"name": "Lactose"})
        IngredientModel.objects.get_or_create(code="SUG", defaults={"name": "Sugar"})
        IngredientModel.objects.get_or_create(code="WAT", defaults={"name": "Water"})

        response = client.post(
            path,
            encode_multipart(BOUNDARY, transparent_post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        drink = DrinkModel.objects.latest("pk")

        assert drink.cost == 2.0
        assert drink.margin == 60.0  # ((5-2)/5)*100
        assert drink.allergens.count() == 2
        assert drink.ingredients.count() == 2
        assert getattr(drink, "nutritional_info").calories == 100

        from core_app.models import DrinkImageModel

        # Check image association
        assert DrinkImageModel.objects.filter(drink=drink).count() == 1
        assert DrinkImageModel.objects.get(drink=drink, is_primary=True).s3_key == drink.photo

    def test_multiple_images(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        transparent_post_data: dict,
        upload_fileobj: MagicMock,
        image: InMemoryUploadedFile,
    ) -> None:
        from core_app.models import DrinkImageModel

        # Add another image
        image2 = InMemoryUploadedFile(
            file=cast(IO[Any], image.file),
            field_name="photos",
            name="test2.jpg",
            content_type="image/jpeg",
            size=image.size,
            charset=None,
        )

        data = transparent_post_data.copy()
        data.pop("photo")
        data["photos"] = [image, image2]

        response = client.post(path, data, format="multipart", **auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        drink = DrinkModel.objects.latest("pk")
        assert DrinkImageModel.objects.filter(drink=drink).count() == 2
        assert upload_fileobj.call_count >= 2
