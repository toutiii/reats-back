from unittest.mock import MagicMock

import pytest
from core_app.models import DrinkModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def drink_id() -> int:
    return 2


@pytest.fixture
def post_data_without_photo() -> dict:
    return {
        "unit": "centiliters",
        "country": "Togo",
        "description": "New description",
        "name": "New name",
        "price": "3",
        "cooker": 1,
        "capacity": "10",
    }


@pytest.mark.django_db
class TestUpdateDrinkWithoutPhotoSuccess:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        drink_id: int,
        path: str,
        post_data_without_photo: dict,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.put(
                f"{path}{drink_id}/",
                encode_multipart(BOUNDARY, post_data_without_photo),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            drink_object = DrinkModel.objects.get(pk=drink_id)

            assert drink_object.country == "Togo"
            assert drink_object.description == "New description"
            assert drink_object.name == "New name"
            assert drink_object.price == 3.0
            assert drink_object.is_enabled is True
            assert drink_object.photo == "cookers/1/drinks/gingembre.jpg"
            assert drink_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"


@pytest.fixture
def post_data_with_photo(image: InMemoryUploadedFile) -> dict:
    return {
        "unit": "centiliters",
        "country": "Togo",
        "description": "New description",
        "name": "New name",
        "price": "3",
        "cooker": 1,
        "capacity": "10",
        "photo": image,
    }


@pytest.mark.django_db
class TestUpdateDrinkWithPhotoSuccess:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        drink_id: int,
        path: str,
        post_data_with_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.put(
                f"{path}{drink_id}/",
                encode_multipart(BOUNDARY, post_data_with_photo),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            drink_object = DrinkModel.objects.get(pk=drink_id)

            assert drink_object.country == "Togo"
            assert drink_object.description == "New description"
            assert drink_object.name == "New name"
            assert drink_object.price == 3.0
            assert drink_object.is_enabled is True
            assert drink_object.photo == "cookers/1/drinks/test.jpg"
            assert drink_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"

            upload_fileobj.assert_called_once()
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "cookers/1/drinks/test.jpg"

            delete_object.assert_called_once_with(
                Bucket="reats-dev-bucket",
                Key="cookers/1/drinks/gingembre.jpg",
            )


@pytest.mark.django_db
class TestUpdateDrinkToDisableState:
    @pytest.fixture
    def drink_post_data(self) -> dict:
        return {"is_enabled": False}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        drink_id: int,
        drink_post_data: dict,
        path: str,
    ):
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{drink_id}/",
                encode_multipart(BOUNDARY, drink_post_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            drink_object = DrinkModel.objects.get(pk=drink_id)

            assert drink_object.is_enabled is False
            assert drink_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"


@pytest.mark.django_db
class TestUpdateDrinkToEnableState:
    @pytest.fixture
    def drink_id(self) -> int:
        return 3

    @pytest.fixture
    def drink_post_data(self) -> dict:
        return {"is_enabled": True}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        drink_id: int,
        drink_post_data: dict,
        path: str,
    ):
        with freeze_time("2023-10-21T22:00:00+00:00"):
            response = client.patch(
                f"{path}{drink_id}/",
                encode_multipart(BOUNDARY, drink_post_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            drink_object = DrinkModel.objects.get(pk=drink_id)

            assert drink_object.is_enabled is True
            assert drink_object.modified.isoformat() == "2023-10-21T22:00:00+00:00"
