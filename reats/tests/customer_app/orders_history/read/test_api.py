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
        "data": [
            {
                "address": {
                    "address_complement": "résidence test",
                    "customer": 1,
                    "id": 2,
                    "postal_code": "91100",
                    "street_name": "rue du terrier du rat",
                    "street_number": "2",
                    "town": "Corbeil-Essonnes",
                },
                "created": "2024-03-02T20:53:05.718117Z",
                "delivery_man": None,
                "delivery_date": "2024-03-10T16:30:00Z",
                "id": 3,
                "items": [
                    {
                        "dish": {
                            "category": "starter",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 1,
                            "is_enabled": True,
                            "name": "Beignets haricots",
                            "photo": "https://some-url.com",
                            "price": 10.0,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "category": "dish",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 2,
                            "is_enabled": True,
                            "name": "Gombo porc riz",
                            "photo": "https://some-url.com",
                            "price": 13.0,
                        },
                        "dish_quantity": 1,
                    },
                    {
                        "drink": {
                            "capacity": 75,
                            "cooker": 1,
                            "country": "Cameroun",
                            "description": "Gingembre maison",
                            "id": 2,
                            "is_enabled": True,
                            "name": "Gingembre",
                            "photo": "https://some-url.com",
                            "price": 5.0,
                            "unit": "centiliters",
                        },
                        "drink_quantity": 4,
                    },
                    {
                        "dish": {
                            "category": "dessert",
                            "cooker": 1,
                            "country": "Italie",
                            "description": "Tiramisu maison au spéculos",
                            "id": 11,
                            "is_enabled": True,
                            "name": "Tiramisu spéculos",
                            "photo": "https://some-url.com",
                            "price": 5.0,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "modified": "2024-03-02T20:53:05.718117Z",
                "order_amount": 58.0,
                "status": "delivered",
            },
            {
                "address": {
                    "address_complement": None,
                    "customer": 1,
                    "id": 3,
                    "postal_code": "91000",
                    "street_name": "rue du terrier du rat",
                    "street_number": "3",
                    "town": "Évry-Courcouronnes",
                },
                "created": "2024-04-02T20:53:05.718117Z",
                "delivery_date": "2024-04-10T16:30:00Z",
                "delivery_man": None,
                "id": 4,
                "items": [
                    {
                        "dish": {
                            "category": "starter",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 1,
                            "is_enabled": True,
                            "name": "Beignets haricots",
                            "photo": "https://some-url.com",
                            "price": 10.0,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "category": "dish",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 2,
                            "is_enabled": True,
                            "name": "Gombo porc riz",
                            "photo": "https://some-url.com",
                            "price": 13.0,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "modified": "2024-04-02T20:53:05.718117Z",
                "order_amount": 33.0,
                "status": "delivered",
            },
            {
                "address": {
                    "address_complement": None,
                    "customer": 1,
                    "id": 4,
                    "postal_code": "91540",
                    "street_name": "rue du terrier du rat",
                    "street_number": "4",
                    "town": "Mennecy",
                },
                "created": "2024-02-02T20:53:05.718117Z",
                "delivery_date": "2024-02-10T16:30:00Z",
                "delivery_man": None,
                "id": 5,
                "items": [
                    {
                        "dish": {
                            "category": "starter",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 1,
                            "is_enabled": True,
                            "name": "Beignets haricots",
                            "photo": "https://some-url.com",
                            "price": 10.0,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "category": "dish",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 2,
                            "is_enabled": True,
                            "name": "Gombo porc riz",
                            "photo": "https://some-url.com",
                            "price": 13.0,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "modified": "2024-02-02T20:53:05.718117Z",
                "order_amount": 33.0,
                "status": "cancelled_by_cooker",
            },
            {
                "address": {
                    "address_complement": None,
                    "customer": 1,
                    "id": 4,
                    "postal_code": "91540",
                    "street_name": "rue du terrier du rat",
                    "street_number": "4",
                    "town": "Mennecy",
                },
                "created": "2024-01-02T20:53:05.718117Z",
                "delivery_date": "2024-01-10T16:30:00Z",
                "delivery_man": None,
                "id": 6,
                "items": [
                    {
                        "dish": {
                            "category": "starter",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 1,
                            "is_enabled": True,
                            "name": "Beignets haricots",
                            "photo": "https://some-url.com",
                            "price": 10.0,
                        },
                        "dish_quantity": 2,
                    },
                    {
                        "dish": {
                            "category": "dish",
                            "cooker": 4,
                            "country": "Cameroun",
                            "description": "Test",
                            "id": 2,
                            "is_enabled": True,
                            "name": "Gombo porc riz",
                            "photo": "https://some-url.com",
                            "price": 13.0,
                        },
                        "dish_quantity": 1,
                    },
                ],
                "modified": "2024-01-02T20:53:05.718117Z",
                "order_amount": 33.0,
                "status": "cancelled_by_customer",
            },
        ],
        "ok": True,
        "status_code": 200,
    }
