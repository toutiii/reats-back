from unittest.mock import MagicMock

import pytest
from core_app.models import DishModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture(params=["starter", "dish", "dessert"])
def category(request) -> str:
    return request.param


@pytest.fixture
def post_data(category: str, image: InMemoryUploadedFile) -> dict:
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
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        post_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        pre_create_count = DishModel.objects.count()

        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert (
            DishModel.objects.latest("pk").photo
            == f"cookers/1/dishes/{post_data.get('category')}/test.jpg"
        )
        upload_fileobj.assert_called_once()
        post_create_count = DishModel.objects.count()

        assert post_create_count - pre_create_count == 1
        assert len(upload_fileobj.call_args.args) == 3

        arg1, arg2, arg3 = upload_fileobj.call_args.args

        assert isinstance(arg1, InMemoryUploadedFile)
        assert arg1.name == "test.jpg"
        assert arg2 == "reats-dev-bucket"
        assert arg3 == f"cookers/1/dishes/{post_data.get('category')}/test.jpg"


@pytest.mark.django_db
class TestCreateDishFailedInvalidCategory:
    @pytest.fixture
    def category(self) -> str:
        return "invalid_category"

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        post_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        pre_create_count = DishModel.objects.count()
        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DishModel.objects.count() == pre_create_count
        upload_fileobj.assert_not_called()
