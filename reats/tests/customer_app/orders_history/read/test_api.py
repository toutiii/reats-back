import pytest
from customer_app.models import OrderModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.mark.django_db
def test_orders_history_list_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_order_history_path: str,
) -> None:

    # we check that the customer has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list customer orders history
    response = client.get(
        customer_order_history_path,
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "ok": True,
        "status_code": 200,
        "data": [
            {
                "id": 3,
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
                "created": "2024-03-02T20:53:05.718117Z",
                "modified": "2024-03-02T20:53:05.718117Z",
                "scheduled_delivery_date": "2024-03-10T16:30:00Z",
                "is_scheduled": False,
                "status": "delivered",
                "cancelled_date": None,
                "delivered_date": "2024-03-02T21:45:05.718117Z",
                "delivery_fees": 3.2,
                "delivery_fees_bonus": 1.5,
                "delivery_man": 1,
                "paid_date": None,
                "stripe_payment_intent_id": None,
                "stripe_payment_intent_secret": None,
                "service_fees": 4.06,
                "sub_total": 58.0,
                "total_amount": 65.26,
            },
            {
                "id": 4,
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
                "created": "2024-04-02T20:53:05.718117Z",
                "modified": "2024-04-02T20:53:05.718117Z",
                "scheduled_delivery_date": "2024-04-10T16:30:00Z",
                "is_scheduled": False,
                "status": "delivered",
                "cancelled_date": None,
                "delivered_date": "2024-03-02T21:45:05.718117Z",
                "delivery_fees": 3.7,
                "delivery_fees_bonus": 1.3,
                "delivery_man": 1,
                "paid_date": None,
                "stripe_payment_intent_id": None,
                "stripe_payment_intent_secret": None,
                "service_fees": 2.31,
                "sub_total": 33.0,
                "total_amount": 39.01,
            },
            {
                "id": 5,
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
                "created": "2024-02-02T20:53:05.718117Z",
                "modified": "2024-02-02T20:53:05.718117Z",
                "is_scheduled": False,
                "status": "cancelled_by_cooker",
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 4.1,
                "delivery_fees_bonus": 1.2,
                "delivery_man": None,
                "paid_date": None,
                "stripe_payment_intent_id": None,
                "stripe_payment_intent_secret": None,
                "scheduled_delivery_date": "2024-02-10T16:30:00Z",
                "service_fees": 2.31,
                "sub_total": 33.0,
                "total_amount": 39.41,
            },
            {
                "id": 6,
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
                "created": "2024-01-02T20:53:05.718117Z",
                "modified": "2024-01-02T20:53:05.718117Z",
                "is_scheduled": False,
                "status": "cancelled_by_customer",
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 4.5,
                "delivery_fees_bonus": 1.1,
                "delivery_man": None,
                "paid_date": None,
                "stripe_payment_intent_id": None,
                "stripe_payment_intent_secret": None,
                "scheduled_delivery_date": "2024-01-10T16:30:00Z",
                "service_fees": 2.31,
                "sub_total": 33.0,
                "total_amount": 39.81,
            },
        ],
    }
