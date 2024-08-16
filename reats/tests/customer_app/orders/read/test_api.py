import pytest
from customer_app.models import OrderModel
from deepdiff import DeepDiff
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
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": False,
                    },
                    "dish_quantity": 2,
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
                    "created": "2024-05-09T20:52:05.718117Z",
                    "address": {
                        "id": 1,
                        "street_name": "rue rené cassin",
                        "street_number": "1",
                        "town": "Corbeil-Essonnes",
                        "postal_code": "91100",
                        "address_complement": "résidence neptune",
                        "customer": 1,
                    },
                    "status": "pending",
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
                        "cooker": 4,
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": False,
                    },
                    "dish_quantity": 1,
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
                    "created": "2024-05-09T20:52:05.718117Z",
                    "address": {
                        "id": 1,
                        "street_name": "rue rené cassin",
                        "street_number": "1",
                        "town": "Corbeil-Essonnes",
                        "postal_code": "91100",
                        "address_complement": "résidence neptune",
                        "customer": 1,
                    },
                    "status": "pending",
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
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": False,
                    },
                    "drink_quantity": 4,
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
                    "created": "2024-05-09T20:52:05.718117Z",
                    "address": {
                        "id": 1,
                        "street_name": "rue rené cassin",
                        "street_number": "1",
                        "town": "Corbeil-Essonnes",
                        "postal_code": "91100",
                        "address_complement": "résidence neptune",
                        "customer": 1,
                    },
                    "status": "pending",
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
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": False,
                    },
                    "dish_quantity": 1,
                    "scheduled_delivery_date": "2024-05-10T12:30:00Z",
                    "created": "2024-05-09T20:52:05.718117Z",
                    "address": {
                        "id": 1,
                        "street_name": "rue rené cassin",
                        "street_number": "1",
                        "town": "Corbeil-Essonnes",
                        "postal_code": "91100",
                        "address_complement": "résidence neptune",
                        "customer": 1,
                    },
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
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": False,
                    },
                    "dish_quantity": 2,
                    "scheduled_delivery_date": "2024-05-20T16:30:00Z",
                    "created": "2024-05-11T20:54:05.718117Z",
                    "address": {
                        "id": 3,
                        "street_name": "Rue Jean Cocteau,",
                        "street_number": "2",
                        "town": "Mennecy",
                        "postal_code": "91540",
                        "address_complement": None,
                        "customer": 2,
                    },
                    "status": "processing",
                }
            ],
            200,
            True,
        ),
        (
            {"status": "completed"},
            [
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
                    "scheduled_delivery_date": "2024-05-17T16:30:00Z",
                    "created": "2024-05-11T20:53:05.718117Z",
                    "address": {
                        "id": 3,
                        "street_name": "Rue Jean Cocteau,",
                        "street_number": "2",
                        "town": "Mennecy",
                        "postal_code": "91540",
                        "address_complement": None,
                        "customer": 2,
                    },
                    "status": "completed",
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
                    "scheduled_delivery_date": "2024-05-17T16:30:00Z",
                    "created": "2024-05-11T20:53:05.718117Z",
                    "address": {
                        "id": 3,
                        "street_name": "Rue Jean Cocteau,",
                        "street_number": "2",
                        "town": "Mennecy",
                        "postal_code": "91540",
                        "address_complement": None,
                        "customer": 2,
                    },
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
    assert response.json().get("ok") == ok_value
    assert response.json().get("status_code") == expected_status_code

    diff = DeepDiff(response.json().get("data"), expected_data, ignore_order=True)

    assert not diff
