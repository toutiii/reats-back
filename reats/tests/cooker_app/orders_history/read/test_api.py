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


@pytest.fixture
def expected_data() -> list[dict]:
    return [
        {
            "id": 12,
            "address": {
                "id": 3,
                "postal_code": "91540",
                "town": "Mennecy",
            },
            "items": [],
            "customer": {
                "id": 1,
                "stripe_id": "cus_QyZ76Ae0W5KeqP",
                "lastname": "TEN",
                "firstname": "Ben",
            },
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "status": "cancelled_by_cooker",
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
            "rating": 0.0,
            "comment": None,
        },
        {
            "id": 14,
            "address": {
                "id": 3,
                "postal_code": "91540",
                "town": "Mennecy",
            },
            "items": [],
            "customer": {
                "id": 1,
                "stripe_id": "cus_QyZ76Ae0W5KeqP",
                "lastname": "TEN",
                "firstname": "Ben",
            },
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "status": "delivered",
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
            "rating": 0.0,
            "comment": None,
        },
        {
            "id": 15,
            "address": {
                "id": 3,
                "postal_code": "91540",
                "town": "Mennecy",
            },
            "items": [],
            "customer": {
                "id": 1,
                "stripe_id": "cus_QyZ76Ae0W5KeqP",
                "lastname": "TEN",
                "firstname": "Ben",
            },
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "status": "delivered",
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
            "rating": 0.0,
            "comment": None,
        },
        {
            "id": 16,
            "address": {
                "id": 3,
                "postal_code": "91540",
                "town": "Mennecy",
            },
            "items": [],
            "customer": {
                "id": 1,
                "stripe_id": "cus_QyZ76Ae0W5KeqP",
                "lastname": "TEN",
                "firstname": "Ben",
            },
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "status": "delivered",
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
            "rating": 0.0,
            "comment": None,
        },
        {
            "id": 17,
            "address": {
                "id": 3,
                "postal_code": "91540",
                "town": "Mennecy",
            },
            "items": [],
            "customer": {
                "id": 1,
                "stripe_id": "cus_QyZ76Ae0W5KeqP",
                "lastname": "TEN",
                "firstname": "Ben",
            },
            "created": "2024-12-11T20:53:05.718117Z",
            "scheduled_delivery_date": "2024-12-17T16:30:00Z",
            "is_scheduled": False,
            "status": "cancelled_by_customer",
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
            "rating": 0.0,
            "comment": None,
        },
    ]


@pytest.mark.django_db
def test_orders_history_list_success_for_cookers(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_history_path: str,
    expected_data: list[dict],
) -> None:

    # we check that the customer has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list customer orders history
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatusEnum.CANCELLED_BY_COOKER,
        OrderStatusEnum.CANCELLED_BY_CUSTOMER,
        OrderStatusEnum.DELIVERED,
    ],
    ids=[
        "fetching orders in cancelled by cooker status",
        "fetching orders in cancelled by customer status",
        "fetching orders in delivered status",
    ],
)
@freeze_time("2024-12-11T02:53:05.718117Z")
def test_orders_list_success_with_order_status_filter(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_history_path: str,
    order_status: OrderStatusEnum,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
        data={"status": order_status},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK

    for order_item in response.json().get("data"):
        assert order_item.get("status") == order_status.value


@pytest.mark.django_db
@freeze_time("2024-12-11T02:53:05.718117Z")
def test_orders_list_success_with_dates_filter_when_some_orders_exist(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_history_path: str,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
        data={
            "start_date": "2024-12-10T00:00:00.000Z",
            "end_date": "2024-12-12T00:00:00.000Z",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert len(response.json().get("data")) > 0


@pytest.mark.django_db
@freeze_time("2024-12-11T02:53:05.718117Z")
def test_orders_list_success_with_dates_filter_when_no_orders_exist(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_history_path: str,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
        data={
            "start_date": "2024-11-10T00:00:00.000Z",
            "end_date": "2024-11-12T00:00:00.000Z",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert len(response.json().get("data")) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_status, start_date, end_date, expected_data",
    [
        (
            OrderStatusEnum.CANCELLED_BY_COOKER,
            "2024-12-10T00:00:00.000Z",
            "2024-12-12T00:00:00.000Z",
            [
                {
                    "id": 12,
                    "address": {
                        "id": 3,
                        "postal_code": "91540",
                        "town": "Mennecy",
                    },
                    "items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "cancelled_by_cooker",
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
                    "rating": 0.0,
                    "comment": None,
                }
            ],
        ),
        (
            OrderStatusEnum.CANCELLED_BY_CUSTOMER,
            "2024-12-10T00:00:00.000Z",
            "2024-12-12T00:00:00.000Z",
            [
                {
                    "id": 17,
                    "address": {
                        "id": 3,
                        "postal_code": "91540",
                        "town": "Mennecy",
                    },
                    "items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "cancelled_by_customer",
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
                    "rating": 0.0,
                    "comment": None,
                }
            ],
        ),
        (
            OrderStatusEnum.DELIVERED,
            "2024-12-10T00:00:00.000Z",
            "2024-12-12T00:00:00.000Z",
            [
                {
                    "id": 14,
                    "address": {
                        "id": 3,
                        "postal_code": "91540",
                        "town": "Mennecy",
                    },
                    "items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "delivered",
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
                    "rating": 0.0,
                    "comment": None,
                },
                {
                    "id": 15,
                    "address": {
                        "id": 3,
                        "postal_code": "91540",
                        "town": "Mennecy",
                    },
                    "items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "delivered",
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
                    "rating": 0.0,
                    "comment": None,
                },
                {
                    "id": 16,
                    "address": {
                        "id": 3,
                        "postal_code": "91540",
                        "town": "Mennecy",
                    },
                    "items": [],
                    "customer": {
                        "id": 1,
                        "stripe_id": "cus_QyZ76Ae0W5KeqP",
                        "lastname": "TEN",
                        "firstname": "Ben",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": "delivered",
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
                    "rating": 0.0,
                    "comment": None,
                },
            ],
        ),
    ],
    ids=[
        "fetching orders in cancelled by cooker status",
        "fetching orders in cancelled by customer status",
        "fetching orders in delivered status",
    ],
)
@freeze_time("2024-12-23T02:53:05.718117Z")
def test_orders_list_success_with_multiple_filters(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cookers_order_history_path: str,
    order_status: OrderStatusEnum,
    start_date: str,
    end_date: str,
    expected_data: list[dict],
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(cooker__id=cooker_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
        data={
            "status": order_status,
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK

    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff
