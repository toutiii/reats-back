import pytest
from cooker_app.models import DishModel
from django.core.exceptions import ObjectDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def dish_id() -> int:
    return 5


@pytest.mark.django_db
class TestSuccessfulDishDeletion:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        path: str,
    ):
        response = client.delete(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, {}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
        }

        with pytest.raises(ObjectDoesNotExist):
            DishModel.objects.get(pk=dish_id)
