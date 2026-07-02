import json
from unittest.mock import MagicMock

import pytest
from core_app.models import DishModel, DishNutritionalInfo, OrderDishItemModel, OrderModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


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
    }


@pytest.mark.django_db
class TestUpdateDishWithoutPhotoSuccess:
    def test_response(
        self,
        auth_headers: dict,
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
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=5)

            assert dish_object.category == "dessert"
            assert dish_object.country == "Togo"
            assert dish_object.description == "New description"
            assert dish_object.name == "New name"
            assert dish_object.price == 14.0
            assert dish_object.is_enabled is True
            assert dish_object.images.first().key == "cookers/1/dishes/dish/poulet-braise.jpg"  # type: ignore
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
        auth_headers: dict,
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
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=dish_id)

            assert dish_object.category == "dessert"
            assert dish_object.country == "Togo"
            assert dish_object.description == "New description"
            assert dish_object.name == "New name"
            assert dish_object.price == 14.0
            assert dish_object.is_enabled is True
            assert dish_object.images.first().key == "cookers/1/dishes/dessert/test.jpg"  # type: ignore
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


@pytest.mark.django_db
class TestUpdateDishToDisableState:
    @pytest.fixture
    def dish_post_state(self) -> bool:
        return False

    @pytest.fixture
    def dish_post_data(self, dish_post_state: bool) -> dict:
        return {"is_enabled": dish_post_state}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        dish_post_data: dict,
        path: str,
    ):
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{dish_id}/",
                encode_multipart(BOUNDARY, dish_post_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=dish_id)

            assert dish_object.is_enabled is False
            assert dish_object.modified.isoformat() == "2023-10-14T22:00:00+00:00"


@pytest.mark.django_db
class TestUpdateDishToEnableState:
    @pytest.fixture
    def dish_id(self) -> int:
        return 12

    @pytest.fixture
    def dish_post_state(self) -> bool:
        return True

    @pytest.fixture
    def dish_post_data(self, dish_post_state: bool) -> dict:
        return {"is_enabled": dish_post_state}

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        dish_post_data: dict,
        path: str,
    ):
        with freeze_time("2023-10-21T22:00:00+00:00"):
            response = client.patch(
                f"{path}{dish_id}/",
                encode_multipart(BOUNDARY, dish_post_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            dish_object = DishModel.objects.get(pk=dish_id)

            assert dish_object.is_enabled is True


@pytest.mark.django_db
class TestUpdateDishNutritionalInfoSuccess:
    @pytest.fixture
    def nutritional_info_update(self) -> dict:
        return {"calories": 400, "proteins": 20, "carbohydrates": 50, "fats": 15}

    def test_put_update_nutritional_info(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        path: str,
        nutritional_info_update: dict,
    ) -> None:
        full_payload = {
            "category": "dessert",
            "cooker": 1,
            "country": "Togo",
            "description": "Updated with nutrition",
            "name": "Updated name",
            "price": "15",
            "nutritional_info": json.dumps(nutritional_info_update),
        }

        response = client.put(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, full_payload),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        dish = DishModel.objects.get(pk=dish_id)
        dish_nutritional_info = DishNutritionalInfo.objects.get(dish=dish)
        for key, value in nutritional_info_update.items():
            assert getattr(dish_nutritional_info, key) == value

    def test_patch_update_nutritional_info(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        path: str,
    ) -> None:
        patch_nutritional_info = {"calories": 500}
        patch_data = {"nutritional_info": json.dumps(patch_nutritional_info)}

        response = client.patch(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, patch_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        dish = DishModel.objects.get(pk=dish_id)
        dish_nutritional_info = DishNutritionalInfo.objects.get(dish=dish)
        for key, value in patch_nutritional_info.items():
            assert getattr(dish_nutritional_info, key) == value


@pytest.mark.django_db
class TestUpdateDishPriceWithOngoingOrderFailure:
    """The price of a dish referenced by an ongoing order is frozen."""

    @pytest.fixture
    def ongoing_order_item(self, dish_id: int) -> OrderDishItemModel:
        order = OrderModel.objects.get(pk=9)
        assert int(order.cooker.id) == 1
        assert order.status == OrderStatusEnum.PENDING
        return OrderDishItemModel.objects.create(order_id=9, dish_id=dish_id, dish_quantity=1)

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        ongoing_order_item: OrderDishItemModel,
        path: str,
    ) -> None:
        original_price = DishModel.objects.get(pk=dish_id).price

        response = client.patch(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, {"price": "20"}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert DishModel.objects.get(pk=dish_id).price == original_price

    def test_other_fields_remain_editable(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        ongoing_order_item: OrderDishItemModel,
        path: str,
        post_data_without_photo: dict,
    ) -> None:
        patch_data = {
            "category": "dessert",
            "description": "New description",
            "name": "New name",
            "cost": "10",
            "preparation_time": 15,
            "max_concurrent_orders": 5,
            "is_enabled": False,
        }

        response = client.patch(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, patch_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        dish_object = DishModel.objects.get(pk=dish_id)
        assert dish_object.category == patch_data["category"]
        assert dish_object.description == patch_data["description"]
        assert dish_object.name == patch_data["name"]
        assert dish_object.cost == 10.0
        assert dish_object.preparation_time == 15
        assert dish_object.max_concurrent_orders == 5
        assert dish_object.is_enabled is False

    def test_unchanged_price_is_allowed(
        self,
        auth_headers: dict,
        client: APIClient,
        dish_id: int,
        ongoing_order_item: OrderDishItemModel,
        path: str,
    ) -> None:
        original_price = DishModel.objects.get(pk=dish_id).price

        response = client.patch(
            f"{path}{dish_id}/",
            encode_multipart(BOUNDARY, {"price": str(original_price), "description": "New text"}),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert DishModel.objects.get(pk=dish_id).description == "New text"
