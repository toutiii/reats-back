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
                            "cooker": 4,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "id": 2,
                            "category": "dish",
                            "country": "Cameroun",
                            "description": "Test",
                            "name": "Gombo porc riz",
                            "price": 13.0,
                            "photo": "https://some-url.com",
                            "is_enabled": True,
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
                            "cooker": 1,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "address": {
                    "id": 2,
                    "street_name": "rue du terrier du rat",
                    "street_number": "2",
                    "town": "Corbeil-Essonnes",
                    "postal_code": "91100",
                    "address_complement": "résidence test",
                    "customer": 1,
                },
                "order_amount": 58.0,
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
                            "cooker": 4,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "id": 2,
                            "category": "dish",
                            "country": "Cameroun",
                            "description": "Test",
                            "name": "Gombo porc riz",
                            "price": 13.0,
                            "photo": "https://some-url.com",
                            "is_enabled": True,
                            "cooker": 4,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "address": {
                    "id": 3,
                    "street_name": "rue du terrier du rat",
                    "street_number": "3",
                    "town": "Évry-Courcouronnes",
                    "postal_code": "91000",
                    "address_complement": None,
                    "customer": 1,
                },
                "order_amount": 33.0,
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
                            "cooker": 4,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "id": 2,
                            "category": "dish",
                            "country": "Cameroun",
                            "description": "Test",
                            "name": "Gombo porc riz",
                            "price": 13.0,
                            "photo": "https://some-url.com",
                            "is_enabled": True,
                            "cooker": 4,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "address": {
                    "id": 4,
                    "street_name": "rue du terrier du rat",
                    "street_number": "4",
                    "town": "Mennecy",
                    "postal_code": "91540",
                    "address_complement": None,
                    "customer": 1,
                },
                "order_amount": 33.0,
                "created": "2024-02-02T20:53:05.718117Z",
                "modified": "2024-02-02T20:53:05.718117Z",
                "scheduled_delivery_date": "2024-02-10T16:30:00Z",
                "is_scheduled": False,
                "status": "cancelled_by_cooker",
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 4.1,
                "delivery_fees_bonus": 1.2,
                "delivery_man": None,
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
                            "cooker": 4,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "id": 2,
                            "category": "dish",
                            "country": "Cameroun",
                            "description": "Test",
                            "name": "Gombo porc riz",
                            "price": 13.0,
                            "photo": "https://some-url.com",
                            "is_enabled": True,
                            "cooker": 4,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "address": {
                    "id": 4,
                    "street_name": "rue du terrier du rat",
                    "street_number": "4",
                    "town": "Mennecy",
                    "postal_code": "91540",
                    "address_complement": None,
                    "customer": 1,
                },
                "order_amount": 33.0,
                "created": "2024-01-02T20:53:05.718117Z",
                "modified": "2024-01-02T20:53:05.718117Z",
                "scheduled_delivery_date": "2024-01-10T16:30:00Z",
                "is_scheduled": False,
                "status": "cancelled_by_customer",
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 4.5,
                "delivery_fees_bonus": 1.1,
                "delivery_man": None,
            },
        ],
    }
