import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from customer_app.models import OrderItemModel, OrderModel
from django.forms import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def address_id() -> int:
    return 2


@pytest.fixture
def post_data_for_order_with_asap_delivery(
    address_id: int,
    customer_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
        "deliveryPlanning": "asap",
    }


@pytest.mark.django_db
def test_create_order_success_with_asap_delivery(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
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
        assert response.status_code == status.HTTP_201_CREATED

        assert model_to_dict(OrderModel.objects.latest("pk")) == {
            "address": 2,
            "cancelled_date": None,
            "completed_date": None,
            "customer": 1,
            "delivered_date": None,
            "delivery_distance": 1390.0,
            "delivery_fees": 1390.0,
            "delivery_fees_bonus": None,
            "delivery_in_progress_date": None,
            "delivery_initial_distance": None,
            "delivery_man": None,
            "id": 9,
            "paid_date": None,
            "is_scheduled": False,
            "processing_date": None,
            "scheduled_delivery_date": None,
            "status": "draft",
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


@pytest.fixture
def post_data_for_order_with_scheduled_delivery(
    address_id: int, customer_id: int
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "deliveryFees": 4.15,
        "deliveryFeesBonus": 1.28,
        "date": "5/10/2024",
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
        "time": "14:30:00",
        "deliveryPlanning": "scheduled",
    }


@pytest.mark.django_db
def test_create_order_success_with_scheduled_delivery(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_scheduled_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
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
        assert model_to_dict(OrderModel.objects.latest("pk")) == {
            "address": 2,
            "cancelled_date": None,
            "completed_date": None,
            "customer": 1,
            "delivered_date": None,
            "delivery_distance": 1390.0,
            "delivery_fees": 1390.0,
            "delivery_fees_bonus": None,
            "delivery_in_progress_date": None,
            "delivery_initial_distance": None,
            "delivery_man": None,
            "id": 10,
            "is_scheduled": True,
            "paid_date": None,
            "processing_date": None,
            "scheduled_delivery_date": datetime(
                2024, 5, 10, 12, 30, tzinfo=timezone.utc
            ),
            "status": "draft",
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
