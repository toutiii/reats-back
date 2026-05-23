from typing import Callable

import pytest
from core_app.models import OrderModel
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum, OrderStatusEnum


@pytest.fixture
def custom_counts() -> dict:
    return {
        OrderStatusEnum.PENDING: 3,
        OrderStatusEnum.ACCEPTED: 2,
        OrderStatusEnum.COMPLETED: 5,
        OrderStatusEnum.CANCELLED: 2,
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
        {"start_date": "2024-01-01", "end_date": "2099-12-31"},
        follow=False,
        **auth_headers,
    )
    assert response.json().get("success") is True
    assert response.json().get("data") == {
        OrderStatusEnum.PENDING.value: 5,
        OrderStatusEnum.ACCEPTED.value: 3,
        OrderStatusEnum.COMPLETED.value: 9,
        OrderStatusEnum.CANCELLED.value: 4,
    }


@pytest.mark.django_db
def test_get_dashboard_data_when_cooker_has_no_orders(
    auth_headers: dict,
    client: APIClient,
    dashboard_path: str,
) -> None:
    OrderModel.objects.filter(cooker_id=1).delete()

    assert OrderModel.objects.filter(cooker_id=1).count() == 0

    response = client.get(
        dashboard_path,
        {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        follow=False,
        **auth_headers,
    )

    assert response.json().get("success") is True
    assert response.json().get("data") == {}


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

    assert response.json().get("success") is False
    assert response.json().get("error").get("code") == ErrorCodeEnum.MISSING_PARAMETERS
    assert response.status_code == status.HTTP_400_BAD_REQUEST
