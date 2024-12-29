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
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers
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
