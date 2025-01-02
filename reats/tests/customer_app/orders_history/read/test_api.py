import pytest
from core_app.models import OrderModel
from deepdiff import DeepDiff
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def expected_data() -> list[dict]:
    return [
        {
            "id": 12,
            "dishes_items": [],
            "drinks_items": [],
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
            "cooker": {
                "id": 1,
                "firstname": "test",
                "lastname": "test",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "rating": 0.0,
            "comment": None,
            "total_amount": 2.4,
        },
        {
            "id": 14,
            "dishes_items": [],
            "drinks_items": [],
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
            "cooker": {
                "id": 1,
                "firstname": "test",
                "lastname": "test",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "rating": 0.0,
            "comment": None,
            "total_amount": 2.4,
        },
        {
            "id": 15,
            "dishes_items": [],
            "drinks_items": [],
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
            "cooker": {
                "id": 1,
                "firstname": "test",
                "lastname": "test",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "rating": 0.0,
            "comment": None,
            "total_amount": 2.4,
        },
        {
            "id": 16,
            "dishes_items": [],
            "drinks_items": [],
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
            "cooker": {
                "id": 1,
                "firstname": "test",
                "lastname": "test",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "rating": 0.0,
            "comment": None,
            "total_amount": 2.4,
        },
        {
            "id": 17,
            "dishes_items": [],
            "drinks_items": [],
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
            "cooker": {
                "id": 1,
                "firstname": "test",
                "lastname": "test",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 0,
            "service_fees": 0.0,
            "rating": 0.0,
            "comment": None,
            "total_amount": 2.4,
        },
        {
            "id": 4,
            "dishes_items": [
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
            "drinks_items": [],
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
            "scheduled_delivery_date": "2024-04-10T16:30:00Z",
            "is_scheduled": False,
            "status": "delivered",
            "processing_date": "2024-03-02T21:15:05.718117Z",
            "completed_date": "2024-03-02T21:25:05.718117Z",
            "delivery_in_progress_date": "2024-03-02T21:33:05.718117Z",
            "cancelled_date": None,
            "delivered_date": "2024-03-02T21:45:05.718117Z",
            "delivery_fees": 3.7,
            "delivery_fees_bonus": 1.3,
            "delivery_distance": 2.5,
            "delivery_initial_distance": 1.5,
            "paid_date": None,
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {
                "id": 4,
                "firstname": "toutii",
                "lastname": "N",
                "acceptance_rate": 100.0,
            },
            "delivery_man": 1,
            "sub_total": 33.0,
            "service_fees": 2.31,
            "rating": 0.0,
            "comment": None,
            "total_amount": 39.01,
        },
        {
            "id": 3,
            "dishes_items": [
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
            "drinks_items": [
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
            "scheduled_delivery_date": "2024-03-10T16:30:00Z",
            "is_scheduled": False,
            "status": "delivered",
            "processing_date": "2024-03-02T21:15:05.718117Z",
            "completed_date": "2024-03-02T21:25:05.718117Z",
            "delivery_in_progress_date": "2024-03-02T21:33:05.718117Z",
            "cancelled_date": None,
            "delivered_date": "2024-03-02T21:45:05.718117Z",
            "delivery_fees": 3.2,
            "delivery_fees_bonus": 1.5,
            "delivery_distance": 3.0,
            "delivery_initial_distance": 2.0,
            "paid_date": None,
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {
                "id": 4,
                "firstname": "toutii",
                "lastname": "N",
                "acceptance_rate": 100.0,
            },
            "delivery_man": 1,
            "sub_total": 58.0,
            "service_fees": 4.06,
            "rating": 0.0,
            "comment": None,
            "total_amount": 65.26,
        },
        {
            "id": 5,
            "dishes_items": [
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
            "drinks_items": [],
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
            "scheduled_delivery_date": "2024-02-10T16:30:00Z",
            "is_scheduled": False,
            "status": "cancelled_by_cooker",
            "processing_date": None,
            "completed_date": None,
            "delivery_in_progress_date": None,
            "cancelled_date": None,
            "delivered_date": None,
            "delivery_fees": 4.1,
            "delivery_fees_bonus": 1.2,
            "delivery_distance": None,
            "delivery_initial_distance": None,
            "paid_date": None,
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {
                "id": 4,
                "firstname": "toutii",
                "lastname": "N",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 33.0,
            "service_fees": 2.31,
            "rating": 0.0,
            "comment": None,
            "total_amount": 39.41,
        },
        {
            "id": 6,
            "dishes_items": [
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
            "drinks_items": [],
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
            "scheduled_delivery_date": "2024-01-10T16:30:00Z",
            "is_scheduled": False,
            "status": "cancelled_by_customer",
            "processing_date": None,
            "completed_date": None,
            "delivery_in_progress_date": None,
            "cancelled_date": None,
            "delivered_date": None,
            "delivery_fees": 4.5,
            "delivery_fees_bonus": 1.1,
            "delivery_distance": None,
            "delivery_initial_distance": None,
            "paid_date": None,
            "stripe_payment_intent_id": None,
            "stripe_payment_intent_secret": None,
            "cooker": {
                "id": 4,
                "firstname": "toutii",
                "lastname": "N",
                "acceptance_rate": 100.0,
            },
            "delivery_man": None,
            "sub_total": 33.0,
            "service_fees": 2.31,
            "rating": 0.0,
            "comment": None,
            "total_amount": 39.81,
        },
    ]


@pytest.mark.django_db
def test_orders_history_list_success_for_customers(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_order_history_path: str,
    expected_data: list[dict],
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
    customer_id: int,
    customer_order_history_path: str,
    order_status: OrderStatusEnum,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        customer_order_history_path,
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
    customer_id: int,
    customer_order_history_path: str,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        customer_order_history_path,
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
    customer_id: int,
    customer_order_history_path: str,
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        customer_order_history_path,
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
                    "address": {
                        "address_complement": None,
                        "customer": 2,
                        "id": 3,
                        "postal_code": "91540",
                        "street_name": "Rue Jean Cocteau",
                        "street_number": "2",
                        "town": "Mennecy",
                    },
                    "cancelled_date": None,
                    "completed_date": None,
                    "cooker": {
                        "acceptance_rate": 100.0,
                        "firstname": "test",
                        "id": 1,
                        "lastname": "test",
                    },
                    "created": "2024-12-11T20:53:05.718117Z",
                    "delivered_date": None,
                    "delivery_distance": None,
                    "delivery_fees": 2.4,
                    "delivery_fees_bonus": 1.1,
                    "delivery_in_progress_date": None,
                    "delivery_initial_distance": None,
                    "delivery_man": None,
                    "id": 12,
                    "is_scheduled": False,
                    "dishes_items": [],
                    "drinks_items": [],
                    "paid_date": None,
                    "processing_date": None,
                    "scheduled_delivery_date": "2024-12-17T16:30:00Z",
                    "service_fees": 0.0,
                    "status": "cancelled_by_cooker",
                    "stripe_payment_intent_id": None,
                    "stripe_payment_intent_secret": None,
                    "sub_total": 0,
                    "rating": 0.0,
                    "comment": None,
                    "total_amount": 2.4,
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
                    "dishes_items": [],
                    "drinks_items": [],
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
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "rating": 0.0,
                    "comment": None,
                    "total_amount": 2.4,
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
                    "dishes_items": [],
                    "drinks_items": [],
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
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "rating": 0.0,
                    "comment": None,
                    "total_amount": 2.4,
                },
                {
                    "id": 15,
                    "dishes_items": [],
                    "drinks_items": [],
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
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "rating": 0.0,
                    "comment": None,
                    "total_amount": 2.4,
                },
                {
                    "id": 16,
                    "dishes_items": [],
                    "drinks_items": [],
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
                    "cooker": {
                        "id": 1,
                        "firstname": "test",
                        "lastname": "test",
                        "acceptance_rate": 100.0,
                    },
                    "delivery_man": None,
                    "sub_total": 0,
                    "service_fees": 0.0,
                    "rating": 0.0,
                    "comment": None,
                    "total_amount": 2.4,
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
    customer_id: int,
    customer_order_history_path: str,
    order_status: OrderStatusEnum,
    start_date: str,
    end_date: str,
    expected_data: list[dict],
) -> None:

    # we check that the cooker has some orders
    assert OrderModel.objects.filter(customer__id=customer_id).count() > 0

    # Then we list cooker orders
    response = client.get(
        customer_order_history_path,
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
