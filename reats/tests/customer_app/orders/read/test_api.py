import pytest
from customer_app.models import OrderModel
from deepdiff import DeepDiff
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status_query_parameter,expected_data,expected_status_code,ok_value",
    [
        (
            {"status": OrderStatusEnum.PENDING},
            [
                {
                    "id": 1,
                    "items": [
                        {
                            "dish": {
                                "id": 1,
                                "category": "starter",
                                "country": "Cameroun",
                                "description": "Test",
                                "name": "Beignets haricots",
                                "price": 10.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 4,
                            },
                            "dish_quantity": 2,
                        },
                        {
                            "dish": {
                                "id": 2,
                                "category": "dish",
                                "country": "Congo",
                                "description": "Test",
                                "name": "Gombo porc riz",
                                "price": 13.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 4,
                            },
                            "dish_quantity": 1,
                        },
                        {
                            "drink": {
                                "id": 2,
                                "unit": "centiliters",
                                "country": "Cameroun",
                                "description": "Gingembre maison",
                                "name": "Gingembre",
                                "price": 5.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "capacity": 75,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 1,
                            },
                            "drink_quantity": 4,
                        },
                        {
                            "dish": {
                                "id": 11,
                                "category": "dessert",
                                "country": "Italie",
                                "description": "Tiramisu maison au spéculos",
                                "name": "Tiramisu spéculos",
                                "price": 5.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 1,
                            },
                            "dish_quantity": 1,
                        },
                    ],
                    "address": {
                        "id": 2,
                        "street_name": "rue des Mazières",
                        "street_number": "13",
                        "town": "Evry",
                        "postal_code": "91000",
                        "address_complement": None,
                        "customer": 1,
                    },
                    "created": "2024-05-09T20:52:05.718117Z",
                    "scheduled_delivery_date": None,
                    "is_scheduled": False,
                    "status": OrderStatusEnum.PENDING,
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 3.19,
                    "delivery_fees_bonus": None,
                    "delivery_distance": 1390.0,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "stripe_payment_intent_id": None,
                    "stripe_payment_intent_secret": None,
                    "cooker": {"id": 4, "firstname": "toutii", "lastname": "N"},
                    "delivery_man": None,
                    "sub_total": 58.0,
                    "service_fees": 4.06,
                    "total_amount": 65.25,
                },
                {
                    "id": 9,
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
                    "status": OrderStatusEnum.PENDING,
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
                    "id": 10,
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
                    "status": OrderStatusEnum.PENDING,
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
            ],
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.PROCESSING},
            [
                {
                    "id": 13,
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
                    "status": OrderStatusEnum.PROCESSING,
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
                    "id": 7,
                    "items": [
                        {
                            "dish": {
                                "id": 1,
                                "category": "starter",
                                "country": "Cameroun",
                                "description": "Test",
                                "name": "Beignets haricots",
                                "price": 10.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 4,
                            },
                            "dish_quantity": 2,
                        }
                    ],
                    "address": {
                        "id": 3,
                        "street_name": "Rue Jean Cocteau",
                        "street_number": "2",
                        "town": "Mennecy",
                        "postal_code": "91540",
                        "address_complement": None,
                        "customer": 2,
                    },
                    "created": "2024-05-11T20:54:05.718117Z",
                    "scheduled_delivery_date": "2024-05-20T16:30:00Z",
                    "is_scheduled": False,
                    "status": OrderStatusEnum.PROCESSING,
                    "processing_date": None,
                    "completed_date": None,
                    "delivery_in_progress_date": None,
                    "cancelled_date": None,
                    "delivered_date": None,
                    "delivery_fees": 2.7,
                    "delivery_fees_bonus": 1.4,
                    "delivery_distance": None,
                    "delivery_initial_distance": None,
                    "paid_date": None,
                    "stripe_payment_intent_id": None,
                    "stripe_payment_intent_secret": None,
                    "cooker": {"id": 4, "firstname": "toutii", "lastname": "N"},
                    "delivery_man": None,
                    "sub_total": 20.0,
                    "service_fees": 1.4,
                    "total_amount": 24.1,
                },
            ],
            200,
            True,
        ),
        (
            {"status": OrderStatusEnum.COMPLETED},
            [
                {
                    "id": 8,
                    "items": [
                        {
                            "dish": {
                                "id": 1,
                                "category": "starter",
                                "country": "Cameroun",
                                "description": "Test",
                                "name": "Beignets haricots",
                                "price": 10.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 4,
                            },
                            "dish_quantity": 2,
                        },
                        {
                            "dish": {
                                "id": 2,
                                "category": "dish",
                                "country": "Congo",
                                "description": "Test",
                                "name": "Gombo porc riz",
                                "price": 13.0,
                                "photo": "https://some-url.com",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": False,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": 4,
                            },
                            "dish_quantity": 1,
                        },
                    ],
                    "address": {
                        "id": 3,
                        "street_name": "Rue Jean Cocteau",
                        "street_number": "2",
                        "town": "Mennecy",
                        "postal_code": "91540",
                        "address_complement": None,
                        "customer": 2,
                    },
                    "created": "2024-05-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-05-17T16:30:00Z",
                    "is_scheduled": False,
                    "status": OrderStatusEnum.COMPLETED,
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
                    "cooker": {"id": 4, "firstname": "toutii", "lastname": "N"},
                    "delivery_man": None,
                    "sub_total": 33.0,
                    "service_fees": 2.31,
                    "total_amount": 37.71,
                },
                {
                    "id": 11,
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
                    "status": OrderStatusEnum.COMPLETED,
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
            ],
            200,
            True,
        ),
        (
            {"status": "invalid"},
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
def test_orders_list_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_order_path: str,
    status_query_parameter: dict,
    expected_data: list[dict],
    expected_status_code: int,
    ok_value: bool,
) -> None:

    # we check that the customer has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list customer orders
    response = client.get(
        customer_order_path,
        follow=False,
        **auth_headers,
        data=status_query_parameter,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") == ok_value
    assert response.json().get("status_code") == expected_status_code
    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff
