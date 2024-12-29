import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from core_app.models import OrderItemModel, OrderModel
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
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
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
                "items": [
                    {
                        "dish_quantity": 1,
                        "drink_quantity": None,
                        "dish": 11,
                        "drink": None,
                    },
                    {
                        "dish_quantity": None,
                        "drink_quantity": 3,
                        "dish": None,
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
            "status": OrderStatusEnum.DRAFT,
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }

        order_item_query = OrderItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )

        assert order_item_query.count() == 2

        for order_item in order_item_query:
            if order_item.dish:
                assert order_item.dish.id == 11
                assert order_item.dish_quantity == 1
            elif order_item.drink:
                assert order_item.drink.id == 2
                assert order_item.drink_quantity == 3
            else:
                assert False, "An order item must be either a dish or a drink"

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
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
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
                "items": [
                    {
                        "dish": 11,
                        "dish_quantity": 1,
                        "drink": None,
                        "drink_quantity": None,
                    },
                    {
                        "dish": None,
                        "dish_quantity": None,
                        "drink": 2,
                        "drink_quantity": 3,
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
            "scheduled_delivery_date": datetime(
                2024, 5, 10, 12, 30, tzinfo=timezone.utc
            ),
            "status": OrderStatusEnum.DRAFT,
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }
        order_item_query = OrderItemModel.objects.filter(
            order__id=OrderModel.objects.latest("pk").pk
        )

        assert order_item_query.count() == 2

        for order_item in order_item_query:
            if order_item.dish:
                assert order_item.dish.id == 11
                assert order_item.dish_quantity == 1
            elif order_item.drink:
                assert order_item.drink.id == 2
                assert order_item.drink_quantity == 3
            else:
                assert False, "An order item must be either a dish or a drink"

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
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
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
