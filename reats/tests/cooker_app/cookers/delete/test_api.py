import pytest
from cooker_app.models import CookerModel, DishModel, DrinkModel
from django.core.exceptions import ObjectDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCookerDeleteSuccess:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33600000001"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        data: dict,
        path: str,
        token_path: str,
    ) -> None:
        cooker_id = 1
        before_delete_count = CookerModel.objects.count()

        with freeze_time("2024-01-20T17:05:45+00:00"):
            # First we ask a token as usual
            token_response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

            response = client.delete(
                f"{path}{cooker_id}/",
                follow=False,
                **access_auth_header,
            )

            after_delete_count = CookerModel.objects.count()

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
            assert before_delete_count - after_delete_count == 1

            with pytest.raises(ObjectDoesNotExist):
                CookerModel.objects.get(pk=cooker_id)

            assert DishModel.objects.filter(cooker__id=cooker_id).count() == 0
            assert DrinkModel.objects.filter(cooker__id=cooker_id).count() == 0
