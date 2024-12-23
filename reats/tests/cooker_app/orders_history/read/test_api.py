import pytest
from customer_app.models import OrderModel
from deepdiff import DeepDiff
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.fixture
def expected_data() -> list[dict]:
    return [
        {
            "id": 12,
            "items": [],
            "address": {
                "id": 3,
                "street_name": "Rue Jean Cocteau",
                "street_number": "2",
                "town": "Mennecy",
                "postal_code": "91540",
                "address_complement": None,
                "customer": 2,
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
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {"id": 1, "firstname": "test", "lastname": "test"},
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "total_amount": 2.4,
        },
        {
            "id": 14,
            "items": [],
            "address": {
                "id": 3,
                "street_name": "Rue Jean Cocteau",
                "street_number": "2",
                "town": "Mennecy",
                "postal_code": "91540",
                "address_complement": None,
                "customer": 2,
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
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {"id": 1, "firstname": "test", "lastname": "test"},
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "total_amount": 2.4,
        },
        {
            "id": 15,
            "items": [],
            "address": {
                "id": 3,
                "street_name": "Rue Jean Cocteau",
                "street_number": "2",
                "town": "Mennecy",
                "postal_code": "91540",
                "address_complement": None,
                "customer": 2,
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
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {"id": 1, "firstname": "test", "lastname": "test"},
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "total_amount": 2.4,
        },
        {
            "id": 16,
            "items": [],
            "address": {
                "id": 3,
                "street_name": "Rue Jean Cocteau",
                "street_number": "2",
                "town": "Mennecy",
                "postal_code": "91540",
                "address_complement": None,
                "customer": 2,
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
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {"id": 1, "firstname": "test", "lastname": "test"},
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "total_amount": 2.4,
        },
        {
            "id": 17,
            "items": [],
            "address": {
                "id": 3,
                "street_name": "Rue Jean Cocteau",
                "street_number": "2",
                "town": "Mennecy",
                "postal_code": "91540",
                "address_complement": None,
                "customer": 2,
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
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {"id": 1, "firstname": "test", "lastname": "test"},
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "total_amount": 2.4,
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
    assert OrderModel.objects.filter(customer__id=cooker_id).count() > 0

    # Then we list customer orders history
    response = client.get(
        cookers_order_history_path,
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff
