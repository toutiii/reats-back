import pytest
from core_app.models import OrderModel
from deepdiff import DeepDiff
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status_query_parameter,expected_data,expected_status_code,ok_value",
    [
        (
            {"status": OrderStatusEnum.PENDING},
            [
                {
                    "id": 9,
                    "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                    "dishes_items": [],
                    "drinks_items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "pending",
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 2.4,
                    "delivery_fees_bonus": 1.1,
                    "delivery_distance": None,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "rating": 0.0,
                    "comment": None,
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "total_amount": 2.4,
                },
                {
                    "id": 10,
                    "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                    "dishes_items": [],
                    "drinks_items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "pending",
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 2.4,
                    "delivery_fees_bonus": 1.1,
                    "delivery_distance": None,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "rating": 0.0,
                    "comment": None,
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "total_amount": 2.4,
                },
            ],
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.PROCESSING},
            [
                {
                    "id": 13,
                    "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                    "dishes_items": [],
                    "drinks_items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "processing",
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 2.4,
                    "delivery_fees_bonus": 1.1,
                    "delivery_distance": None,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "rating": 0.0,
                    "comment": None,
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "total_amount": 2.4,
                },
            ],
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.COMPLETED},
            [
                {
                    "id": 11,
                    "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                    "dishes_items": [],
                    "drinks_items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "completed",
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 2.4,
                    "delivery_fees_bonus": 1.1,
                    "delivery_distance": None,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "rating": 0.0,
                    "comment": None,
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "total_amount": 2.4,
                },
            ],
            200,
            True,
        ),
        (
            {
                "status": "invalid",
            },
            [],
            200,
            True,
        ),
    ],
    ids=[
        "fetching orders in pending status",
        "fetching orders in processing status",
        "fetching orders in completed status",
        "fetching orders with invalid status",
    ],
)
@freeze_time("2024-12-11T02:53:05.718117Z")
def test_orders_list_success_with_no_filters(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_path: str,
    status_query_parameter: dict,
    expected_data: list[dict],
    expected_status_code: int,
    ok_value: bool,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        cookers_order_path,
        follow=False,
        **auth_headers,
        data=status_query_parameter,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("success") is True

    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff
