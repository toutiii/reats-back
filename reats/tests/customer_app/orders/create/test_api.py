import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from core_app.models import OrderDishItemModel, OrderDrinkItemModel, OrderModel
from django.forms import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum

# Add this line to ignore E501 errors
# flake8: noqa: E501


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def address_id() -> int:
    return 2


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.fixture
def post_data_for_order_with_asap_delivery(
    address_id: int,
    customer_id: int,
    cooker_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "cookerID": cooker_id,
        "dishes_items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
            ]
        ),
        "drinks_items": json.dumps(
            [
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }


@pytest.mark.django_db
def test_create_order_success_with_asap_delivery(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_data_for_order_with_asap_delivery,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        api_response: dict = response.json()
        assert api_response["data"].pop("id") is not None
        assert api_response == {
            "ok": True,
            "status_code": 200,
            "data": {
                "dishes_items": [
                    {
                        "dish_quantity": 1,
                        "dish": 11,
                    },
                ],
                "drinks_items": [
                    {
                        "drink_quantity": 3,
                        "drink": 2,
                    },
                ],
                "scheduled_delivery_date": None,
                "is_scheduled": False,
                "processing_date": None,
                "completed_date": None,
                "delivery_in_progress_date": None,
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 3.19,
                "delivery_distance": 1390.0,
                "delivery_initial_distance": None,
                "paid_date": None,
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "address": 2,
                "delivery_man": None,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "sub_total": 20.0,
                "total_amount": 24.59,
                "service_fees": 1.4,
                "rating": 0.0,
                "comment": None,
            },
        }
        order_dict = model_to_dict(OrderModel.objects.latest("pk"))
        del order_dict["id"]

        assert order_dict == {
            "address": 2,
            "cancelled_date": None,
            "completed_date": None,
            "customer": 1,
            "cooker": 1,
            "delivered_date": None,
            "delivery_distance": 1390.0,
            "delivery_fees": 3.19,
            "delivery_fees_bonus": None,
            "delivery_in_progress_date": None,
            "delivery_initial_distance": None,
            "delivery_man": None,
            "paid_date": None,
            "is_scheduled": False,
            "processing_date": None,
            "scheduled_delivery_date": None,
            "rating": 0.0,
            "comment": None,
            "status": OrderStatusEnum.DRAFT.value,
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }

        order_dish_item_query = OrderDishItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )
        order_drink_item_query = OrderDrinkItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )

        assert order_dish_item_query.count() == 1
        assert order_drink_item_query.count() == 1

        for order_dish_item in order_dish_item_query:
            assert order_dish_item.dish.id == 11
            assert order_dish_item.dish_quantity == 1

        for order_drink_item in order_drink_item_query:
            assert order_drink_item.drink.id == 2
            assert order_drink_item.drink_quantity == 3

        mock_googlemaps_distance_matrix.assert_called_once_with(
            origins=["13 rue des Mazières 91000 Evry"],
            destinations=["1 rue André Lalande 91000 Evry"],
        )
        mock_stripe_payment_intent_create.assert_called_once_with(
            amount=2459,
            currency="EUR",
            automatic_payment_methods={"enabled": True},
            customer="cus_QyZ76Ae0W5KeqP",
        )
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_QyZ76Ae0W5KeqP",
            stripe_version="2024-06-20",
        )


@pytest.fixture
def post_data_for_order_with_scheduled_delivery(
    address_id: int,
    customer_id: int,
    cooker_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "cookerID": cooker_id,
        "date": "5/10/2024",
        "time": "14:30:00",
        "dishes_items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
            ]
        ),
        "drinks_items": json.dumps(
            [
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }


@pytest.mark.django_db
def test_create_order_success_with_scheduled_delivery(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_scheduled_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
) -> None:

    with freeze_time("2024-05-09T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            encode_multipart(BOUNDARY, post_data_for_order_with_scheduled_delivery),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        api_response: dict = response.json()
        assert api_response["data"].pop("id") is not None
        assert api_response == {
            "data": {
                "address": 2,
                "cancelled_date": None,
                "completed_date": None,
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "delivered_date": None,
                "delivery_distance": 1390.0,
                "delivery_fees": 3.19,
                "delivery_in_progress_date": None,
                "delivery_initial_distance": None,
                "delivery_man": None,
                "is_scheduled": True,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "sub_total": 20.0,
                "total_amount": 24.59,
                "service_fees": 1.4,
                "rating": 0.0,
                "comment": None,
                "dishes_items": [
                    {
                        "dish_quantity": 1,
                        "dish": 11,
                    },
                ],
                "drinks_items": [
                    {
                        "drink_quantity": 3,
                        "drink": 2,
                    },
                ],
                "paid_date": None,
                "processing_date": None,
                "scheduled_delivery_date": "2024-05-10T12:30:00Z",
            },
            "ok": True,
            "status_code": 200,
        }
        order_dict = model_to_dict(OrderModel.objects.latest("pk"))
        del order_dict["id"]
        assert order_dict == {
            "address": 2,
            "cancelled_date": None,
            "completed_date": None,
            "customer": 1,
            "cooker": 1,
            "delivered_date": None,
            "delivery_distance": 1390.0,
            "delivery_fees": 3.19,
            "delivery_fees_bonus": None,
            "delivery_in_progress_date": None,
            "delivery_initial_distance": None,
            "delivery_man": None,
            "is_scheduled": True,
            "paid_date": None,
            "processing_date": None,
            "rating": 0.0,
            "comment": None,
            "scheduled_delivery_date": datetime(
                2024, 5, 10, 12, 30, tzinfo=timezone.utc
            ),
            "status": OrderStatusEnum.DRAFT.value,
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }

        order_dish_item_query = OrderDishItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )
        order_drink_item_query = OrderDrinkItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )

        assert order_dish_item_query.count() == 1
        assert order_drink_item_query.count() == 1

        for order_dish_item in order_dish_item_query:
            assert order_dish_item.dish.id == 11
            assert order_dish_item.dish_quantity == 1

        for order_drink_item in order_drink_item_query:
            assert order_drink_item.drink.id == 2
            assert order_drink_item.drink_quantity == 3

        mock_googlemaps_distance_matrix.assert_called_once_with(
            origins=["13 rue des Mazières 91000 Evry"],
            destinations=["1 rue André Lalande 91000 Evry"],
        )

        mock_stripe_payment_intent_create.assert_called_once_with(
            amount=2459,
            currency="EUR",
            automatic_payment_methods={"enabled": True},
            customer="cus_QyZ76Ae0W5KeqP",
        )
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_QyZ76Ae0W5KeqP",
            stripe_version="2024-06-20",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "date, time, expected_status_code",
    [
        (
            "5/08/2024",
            "14:30:00",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            "09/08/2024",
            "12:30:00",
            status.HTTP_400_BAD_REQUEST,
        ),
    ],
    ids=[
        "scheduled order is in the past",
        "scheduler order is the same day but prior to the current htime",
    ],
)
def test_create_scheduled_order_failed_with_wrong_delivery_infos(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    mock_googlemaps_distance_matrix: MagicMock,
    address_id: int,
    customer_id: int,
    date: str,
    time: str,
    expected_status_code: int,
    mock_stripe_payment_intent_create: MagicMock,
) -> None:

    scheduled_order_data: dict = {
        "addressID": address_id,
        "customerID": customer_id,
        "date": date,
        "time": time,
        "dishes_items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
            ]
        ),
        "drinks_items": json.dumps(
            [
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }

    with freeze_time("2024-09-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            encode_multipart(BOUNDARY, scheduled_order_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == expected_status_code
        mock_googlemaps_distance_matrix.assert_not_called()
        mock_stripe_payment_intent_create.assert_not_called()
