from unittest.mock import MagicMock

from freezegun import freeze_time

import pytest
from cooker_app.models import DishModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def dish_id() -> int:
    return 5


@pytest.fixture
def post_data_without_photo() -> dict:
    return {
        "category": "dessert",
        "cooker": 1,
        "country": "Togo",
        "description": "New description",
        "name": "New name",
        "price": "14",
        "is_enabled": True,
    }


@pytest.mark.django_db
class TestUpdateDishWithoutPhotoSuccess:
    def test_response(
        self,
        client: APIClient,
        dish_id: int,
        path: str,
        post_data_without_photo: dict,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.put(
                f"{path}{dish_id}/",
                encode_multipart(BOUNDARY, post_data_without_photo),
                content_type=MULTIPART_CONTENT,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=5)

            assert dish_object.category == "dessert"
            assert dish_object.country == "Togo"
            assert dish_object.description == "New description"
            assert dish_object.name == "New name"
            assert dish_object.price == 14.0
            assert dish_object.is_enabled is True
            assert dish_object.photo == "cookers/1/dishes/dish/poulet-braise.jpg"
            assert dish_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"


@pytest.fixture
def post_data_with_photo(image: InMemoryUploadedFile) -> dict:
    return {
        "category": "dessert",
        "cooker": 1,
        "country": "Togo",
        "description": "New description",
        "name": "New name",
        "price": "14",
        "photo": image,
        "is_enabled": True,
    }


@pytest.mark.django_db
class TestUpdateDishWithPhotoSuccess:
    def test_response(
        self,
        client: APIClient,
        delete_object: MagicMock,
        dish_id: int,
        path: str,
        post_data_with_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.put(
                f"{path}{dish_id}/",
                encode_multipart(BOUNDARY, post_data_with_photo),
                content_type=MULTIPART_CONTENT,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=5)

            assert dish_object.category == "dessert"
            assert dish_object.country == "Togo"
            assert dish_object.description == "New description"
            assert dish_object.name == "New name"
            assert dish_object.price == 14.0
            assert dish_object.is_enabled is True
            assert dish_object.photo == "cookers/1/dishes/dessert/test.jpg"
            assert dish_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"

            upload_fileobj.assert_called_once()
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "cookers/1/dishes/dessert/test.jpg"

            delete_object.assert_called_once_with(
                Bucket="reats-dev-bucket",
                Key="cookers/1/dishes/dish/poulet-braise.jpg",
            )
