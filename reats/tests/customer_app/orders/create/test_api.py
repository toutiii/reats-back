import json

import pytest
from customer_app.models import CustomerModel, OrderItemModel, OrderModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def address_id() -> int:
    return 3


@pytest.fixture
def post_data(address_id: int, customer_id: int) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "date": "5/10/2024",
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
        "time": "14:30:00",
    }


@pytest.mark.django_db
def test_create_order_success(
    auth_headers: dict,
    client: APIClient,
    address_id: int,
    customer_id: int,
    customer_order_path: str,
    post_data: dict,
) -> None:
    old_count = OrderModel.objects.count()

    with freeze_time("2024-05-08T10:16:00+00:00"):
        old_count = OrderModel.objects.count()
        response = client.post(
            customer_order_path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        new_count = OrderModel.objects.count()

        assert new_count - old_count == 1
        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.delivery_date.isoformat() == "2024-05-10T12:30:00+00:00"
        assert order.customer.pk == customer_id
        assert order.address.pk == address_id
        assert order.status == "pending"

        assert CustomerModel.objects.get(pk=customer_id).orders.count() > 0
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
