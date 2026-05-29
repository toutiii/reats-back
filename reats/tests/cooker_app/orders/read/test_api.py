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
            {
                "results": [
                    {
                        "id": 9,
                        "status": "pending",
                        "created": "2024-12-11T20:53:05.718117Z",
                        "customer": {
                            "id": 1,
                            "lastname": "TEN",
                            "firstname": "Ben",
                        },
                        "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                        "dishes_items": [],
                        "drinks_items": [],
                        "items_count": 0,
                        "sub_total": 0.0,
                        "delivery_fees": 2.4,
                        "service_fees": 0.0,
                        "total_amount": 2.4,
                    },
                    {
                        "id": 10,
                        "status": "pending",
                        "created": "2024-12-11T20:53:05.718117Z",
                        "customer": {
                            "id": 1,
                            "lastname": "TEN",
                            "firstname": "Ben",
                        },
                        "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                        "dishes_items": [],
                        "drinks_items": [],
                        "items_count": 0,
                        "sub_total": 0.0,
                        "delivery_fees": 2.4,
                        "service_fees": 0.0,
                        "total_amount": 2.4,
                    },
                ],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 1,
                    "total_items": 2,
                    "items_per_page": 10,
                },
            },
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.ACCEPTED},
            {
                "results": [
                    {
                        "id": 13,
                        "status": "accepted",
                        "created": "2024-12-11T20:53:05.718117Z",
                        "customer": {
                            "id": 1,
                            "lastname": "TEN",
                            "firstname": "Ben",
                        },
                        "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
                        "dishes_items": [],
                        "drinks_items": [],
                        "items_count": 0,
                        "sub_total": 0.0,
                        "delivery_fees": 2.4,
                        "service_fees": 0.0,
                        "total_amount": 2.4,
                    },
                ],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 1,
                    "total_items": 1,
                    "items_per_page": 10,
                },
            },
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.COMPLETED},
            {
                "results": [],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 1,
                    "total_items": 0,
                    "items_per_page": 10,
                },
            },
            200,
            True,
        ),
        (
            {
                "status": "invalid",
            },
            {
                "results": [],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 1,
                    "total_items": 0,
                    "items_per_page": 10,
                },
            },
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


@pytest.fixture
def other_cooker_id() -> int:
    return 4


@pytest.mark.django_db
def test_retrieve_order_success(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_path: str,
) -> None:
    order = OrderModel.objects.filter(cooker__id=cooker_id).first()
    assert order is not None, "Aucune commande trouvée pour ce cooker dans les fixtures"

    url = f"{cookers_order_path}{order.id}/"

    response = client.get(url, **auth_headers)
    assert response.status_code == status.HTTP_200_OK

    assert response.json() == {
        "success": True,
        "message": "Operation successful",
        "data": {
            "id": order.id,
            "status": order.status,
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "accepted_date": None,
            "preparing_date": None,
            "ready_date": None,
            "delivering_date": None,
            "completed_date": None,
            "cancelled_date": None,
            "cancelled_by": None,
            "paid_date": None,
            "rating": 0.0,
            "comment": None,
            "delivery_man": None,
            "delivery_fees": 2.4,
            "delivery_fees_bonus": 1.1,
            "delivery_distance": None,
            "delivery_initial_distance": None,
            "customer": {"id": 1, "lastname": "TEN", "firstname": "Ben"},
            "address": {"id": 3, "postal_code": "91540", "town": "Mennecy"},
            "dishes_items": [],
            "drinks_items": [],
            "items_count": 0,
            "sub_total": 0.0,
            "service_fees": 0.0,
            "total_amount": 2.4,
        },
    }


@pytest.mark.django_db
def test_retrieve_order_not_found_for_other_cooker_order(
    auth_headers: dict,
    client: APIClient,
    other_cooker_id: int,
    cookers_order_path: str,
) -> None:
    # Pick an order belonging to ANOTHER cooker
    order = OrderModel.objects.filter(cooker__id=other_cooker_id).first()
    assert order is not None

    url = f"{cookers_order_path}{order.id}/"

    response = client.get(
        url,
        follow=False,
        **auth_headers,
    )

    # Should return 404 because of queryset filtering
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("success") is False
