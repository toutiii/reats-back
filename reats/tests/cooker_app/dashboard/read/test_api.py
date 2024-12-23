from typing import Callable

import pytest
from customer_app.models import OrderModel
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


@pytest.fixture
def custom_counts() -> dict:
    return {
        OrderStatusEnum.PENDING: 3,
        OrderStatusEnum.PROCESSING: 2,
        OrderStatusEnum.COMPLETED: 4,
        OrderStatusEnum.CANCELLED_BY_COOKER: 2,
        OrderStatusEnum.DELIVERED: 1,
    }


@pytest.mark.django_db
def test_get_dashboard_data_when_cooker_has_orders(
    auth_headers: dict,
    client: APIClient,
    dashboard_path: str,
    create_orders: Callable,
    custom_counts: dict,
) -> None:

    response = client.get(
        dashboard_path,
        {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        follow=False,
        **auth_headers,
    )

    assert response.json() == {
        "ok": True,
        "status_code": 200,
        "data": {
            OrderStatusEnum.CANCELLED_BY_COOKER: 3,
            OrderStatusEnum.CANCELLED_BY_CUSTOMER: 1,
            OrderStatusEnum.COMPLETED: 5,
            OrderStatusEnum.PENDING: 5,
            OrderStatusEnum.DELIVERED: 4,
            OrderStatusEnum.PROCESSING: 3,
        },
    }


@pytest.mark.django_db
def test_get_dashboard_data_when_cooker_has_no_orders(
    auth_headers: dict,
    client: APIClient,
    dashboard_path: str,
) -> None:

    # First we delete all orders for cooker_id=1 to ensure
    # that the cooker has no orders.

    OrderModel.objects.filter(cooker_id=1).delete()

    assert OrderModel.objects.filter(cooker_id=1).count() == 0

    response = client.get(
        dashboard_path,
        {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        follow=False,
        **auth_headers,
    )

    assert response.json() == {
        "ok": True,
        "status_code": status.HTTP_200_OK,
        "data": {},
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_parameter",
    [
        {},
        {"start_date": "2024-01-01"},
        {"end_date": "2024-12-31"},
    ],
    ids=[
        "no_dates",
        "missing_end_date",
        "missing_start_date",
    ],
)
def test_get_dashboard_data_fails_when_a_date_is_missing(
    auth_headers: dict,
    client: APIClient,
    dashboard_path: str,
    query_parameter: dict,
) -> None:

    response = client.get(
        dashboard_path,
        query_parameter,
        follow=False,
        **auth_headers,
    )

    assert response.json() == {
        "ok": False,
        "status_code": status.HTTP_400_BAD_REQUEST,
    }
