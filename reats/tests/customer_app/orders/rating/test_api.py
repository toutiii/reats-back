import json
from unittest.mock import MagicMock

import pytest
from core_app.models import DishRatingModel, DrinkRatingModel, OrderModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


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
def post_order_data(
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
def test_add_rates_to_orders_and_orders_items(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    customer_orders_dish_rating_path: str,
    customer_orders_drink_rating_path: str,
    customer_orders_rating_path: str,
    post_order_data: dict,
    customer_id: int,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a delivered order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    # Then we switch the order to pending few minutes later
    with freeze_time("2024-05-08T10:18:00+00:00"):
        order.status = OrderStatusEnum.PENDING.value
        order.save()

    # Then we switch the order to processing few minutes later
    with freeze_time("2024-05-08T10:20:00+00:00"):
        order.status = OrderStatusEnum.PROCESSING.value
        order.save()

    # Then we switch the order to completed few minutes later
    with freeze_time("2024-05-08T10:22:00+00:00"):
        order.status = OrderStatusEnum.COMPLETED.value
        order.save()

    # Then we switch the order to delivered few minutes later
    with freeze_time("2024-05-08T10:24:00+00:00"):
        order.status = OrderStatusEnum.DELIVERED.value
        order.save()

    assert order.status == OrderStatusEnum.DELIVERED.value

    # We update order to add overall rating infos
    order_rating_data: dict = {
        "order_id": order.id,
        "rating": 5,
        "comment": "Excellent",
    }
    update_order_response = client.put(
        f"{customer_orders_rating_path}{order.id}/",
        encode_multipart(BOUNDARY, order_rating_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert update_order_response.status_code == status.HTTP_200_OK
    assert update_order_response.json() == {
        "ok": True,
        "status_code": 200,
    }

    order.refresh_from_db()
    assert order.rating == order_rating_data["rating"]
    assert order.comment == order_rating_data["comment"]

    # We add infos in dish ratings table
    dish_rating_data: dict = {
        "dish_ids": [11],
        "ratings": [3],
        "comments": ["Good"],
        "customer_id": customer_id,
    }

    create_dish_rating_response = client.post(
        f"{customer_orders_dish_rating_path}",
        encode_multipart(BOUNDARY, dish_rating_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )

    assert create_dish_rating_response.status_code == status.HTTP_201_CREATED
    assert create_dish_rating_response.json() == {
        "ok": True,
        "status_code": 201,
    }

    for idx in range(len(dish_rating_data["dish_ids"])):
        dish_rating_instance: DishRatingModel = DishRatingModel.objects.get(
            dish_id=dish_rating_data["dish_ids"][idx]
        )
        assert dish_rating_instance.rating == dish_rating_data["ratings"][idx]
        assert dish_rating_instance.comment == dish_rating_data["comments"][idx]

    # We add infos in drink ratings table
    drink_rating_data: dict = {
        "drink_ids": [2],
        "ratings": [4],
        "comments": ["Very good"],
        "customer_id": customer_id,
    }

    create_drink_rating_response = client.post(
        f"{customer_orders_drink_rating_path}",
        encode_multipart(BOUNDARY, drink_rating_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert create_drink_rating_response.status_code == status.HTTP_201_CREATED
    assert create_drink_rating_response.json() == {
        "ok": True,
        "status_code": 201,
    }

    for idx in range(len(drink_rating_data["drink_ids"])):
        drink_rating_instance: DrinkRatingModel = DrinkRatingModel.objects.get(
            drink_id=drink_rating_data["drink_ids"][idx]
        )
        assert drink_rating_instance.rating == drink_rating_data["ratings"][idx]
        assert drink_rating_instance.comment == drink_rating_data["comments"][idx]

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_not_called()
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
