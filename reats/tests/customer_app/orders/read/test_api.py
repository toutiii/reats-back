import pytest
from customer_app.models import OrderModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status_query_parameter,expected_data,expected_status_code,ok_value",
    [
        (
            {"status": "pending"},
            [
                {
                    "address": {
                        "address_complement": "résidence test",
                        "customer": 1,
                        "id": 1,
                        "postal_code": "91100",
                        "street_name": "rue du terrier du rat",
                        "street_number": "1",
                        "town": "Villabé",
                    },
                    "created": "2024-05-09T20:52:05.718117Z",
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
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
                    "status": "pending",
                },
                {
                    "address": {
                        "address_complement": "résidence test",
                        "customer": 1,
                        "id": 1,
                        "postal_code": "91100",
                        "street_name": "rue du terrier du rat",
                        "street_number": "1",
                        "town": "Villabé",
                    },
                    "created": "2024-05-09T20:52:05.718117Z",
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
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
                    "status": "pending",
                },
                {
                    "address": {
                        "address_complement": "résidence test",
                        "customer": 1,
                        "id": 1,
                        "postal_code": "91100",
                        "street_name": "rue du terrier du rat",
                        "street_number": "1",
                        "town": "Villabé",
                    },
                    "created": "2024-05-09T20:52:05.718117Z",
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
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
                    "status": "pending",
                },
                {
                    "address": {
                        "address_complement": "résidence test",
                        "customer": 1,
                        "id": 1,
                        "postal_code": "91100",
                        "street_name": "rue du terrier du rat",
                        "street_number": "1",
                        "town": "Villabé",
                    },
                    "created": "2024-05-09T20:52:05.718117Z",
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
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
                    "status": "pending",
                },
            ],
            200,
            True,
        ),
        (
            {"status": "processing"},
            [
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
                    "created": "2024-05-11T20:54:05.718117Z",
                    "scheduled_delivery_date": "2024-05-20T16:30:00Z",
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
                    "status": "processing",
                },
            ],
            200,
            True,
        ),
        (
            {"status": "completed"},
            [
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
                    "created": "2024-05-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-05-17T16:30:00Z",
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
                    "status": "completed",
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
                    "created": "2024-05-11T20:53:05.718117Z",
                    "scheduled_delivery_date": "2024-05-17T16:30:00Z",
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
                    "status": "completed",
                },
            ],
            200,
            True,
        ),
        (
            {"status": "invalid"},
            [],
            404,
            False,
        ),
    ],
    ids=[
        "fetching orders in pending status",
        "fetching orders in processing status",
        "fetching orders in completed status",
        "fetching orders with invalid status",
    ],
)
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
    assert response.json() == {
        "data": expected_data,
        "ok": ok_value,
        "status_code": expected_status_code,
    }
