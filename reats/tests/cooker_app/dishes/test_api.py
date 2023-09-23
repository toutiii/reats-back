from io import BytesIO
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from cooker_app.models import DishModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def path() -> str:
    return "/api/v1/dishes/"


@pytest.fixture
def upload_fileobj() -> Iterator:
    patcher = patch("cooker_app.views.s3.upload_fileobj")
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def post_data(category: str) -> dict:
    im = Image.new(mode="RGB", size=(200, 200))  # create a new image using PIL
    im_io = BytesIO()  # a BytesIO object for saving image
    im.save(im_io, "JPEG")  # save the image to im_io
    im_io.seek(0)  # seek to the beginning

    image = InMemoryUploadedFile(
        im_io, None, "test.jpg", "image/jpeg", len(im_io.getvalue()), None
    )
    return {
        "category": category,
        "cooker": 1,
        "country": "Cameroun",
        "description": "Test",
        "name": "Beignets haricots",
        "photo": image,
        "price": "10",
    }


@pytest.mark.django_db
class TestCreateDishSuccess:
    @pytest.fixture(params=["starter", "main_dish", "dessert"])
    def category(self, request) -> str:
        return request.param

    def test_response(
        self,
        category: str,
        client: APIClient,
        path: str,
        post_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with upload_fileobj as upload_fileobj:
            response = client.post(
                path,
                encode_multipart(BOUNDARY, post_data),
                content_type=MULTIPART_CONTENT,
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert DishModel.objects.count() == 1
            assert (
                DishModel.objects.latest("pk").photo
                == f"https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/1/dishes/{category}/test.jpg"
            )
            upload_fileobj.assert_not_called()


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
        upload_fileobj: MagicMock,
    ) -> None:
        with upload_fileobj as upload_fileobj:
            response = client.post(
                path,
                encode_multipart(BOUNDARY, post_data),
                content_type=MULTIPART_CONTENT,
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DishModel.objects.count() == 0
        upload_fileobj.assert_not_called()
