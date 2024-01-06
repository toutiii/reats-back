import pytest
from cooker_app.models import DrinkModel
from django.core.exceptions import ObjectDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def drink_id() -> int:
    return 2


@pytest.mark.django_db
class TestSuccessfulDishDeletion:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        drink_id: int,
        path: str,
    ):
        response = client.delete(
            f"{path}{drink_id}/",
            encode_multipart(BOUNDARY, {}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_204_NO_CONTENT,
        }

        with pytest.raises(ObjectDoesNotExist):
            DrinkModel.objects.get(pk=drink_id)
