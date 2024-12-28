import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from cooker_app.models import CookerModel
from customer_app.models import OrderModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import OrderStatusEnum

# Add this line to ignore E501 errors
# flake8: noqa: E501


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def address_id() -> int:
    return 2


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.fixture
def post_order_data(
    address_id: int,
    customer_id: int,
    cooker_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "cookerID": cooker_id,
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }


@pytest.mark.django_db
def test_update_order_from_pending_to_cancelled_by_cooker_status(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        # Then we switch the order to pending few minutes later
        order.status = OrderStatusEnum.PENDING.value
        order.save()

    with freeze_time("2024-05-08T10:41:00+00:00"):
        # Then we switch the order to cancelled by cooker few minutes later
        update_status_data = {
            "status": OrderStatusEnum.CANCELLED_BY_COOKER.value,
        }
        update_to_cancelled_by_cooker_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_cancelled_by_cooker_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.CANCELLED_BY_COOKER.value
        assert order.cancelled_date == datetime(
            2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc
        )
        assert order

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_called_once_with(
        amount=2319,
        payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
    )
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        customer="cus_QyZ76Ae0W5KeqP",
    )


@pytest.mark.django_db
def test_update_order_from_processing_to_cancelled_by_cooker_status(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    # Manually set the order to PENDING status
    order.status = OrderStatusEnum.PENDING.value
    order.save()

    assert order.status == OrderStatusEnum.PENDING.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_to_processing_state_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.PROCESSING.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_processing_state_response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.PROCESSING.value
    assert order.processing_date == datetime(
        2024,
        5,
        8,
        10,
        18,
        0,
        tzinfo=timezone.utc,
    )

    with freeze_time("2024-05-08T10:20:00+00:00"):
        update_to_cancelled_by_cooker_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.CANCELLED_BY_COOKER.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert update_to_cancelled_by_cooker_response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.CANCELLED_BY_COOKER.value
    assert order.cancelled_date == datetime(
        2024,
        5,
        8,
        10,
        20,
        0,
        tzinfo=timezone.utc,
    )
    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_called_once_with(
        amount=2319,
        payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
    )
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        customer="cus_QyZ76Ae0W5KeqP",
    )


@pytest.mark.django_db
def test_update_order_from_pending_to_processing_state(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    # Manually set the order to PENDING status
    order.status = OrderStatusEnum.PENDING.value
    order.save()

    assert order.status == OrderStatusEnum.PENDING.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_to_processing_state_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.PROCESSING.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_processing_state_response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.PROCESSING.value
    assert order.processing_date == datetime(
        2024,
        5,
        8,
        10,
        18,
        0,
        tzinfo=timezone.utc,
    )
    mock_googlemaps_distance_matrix.assert_called_once()
    mock_stripe_payment_intent_create.assert_called_once()
    mock_stripe_create_refund_success.assert_not_called()


@pytest.mark.django_db
def test_update_order_from_pending_to_completed_state(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    # Manually set the order to PENDING status
    order.status = OrderStatusEnum.PENDING.value
    order.save()

    assert order.status == OrderStatusEnum.PENDING.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_to_processing_state_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.PROCESSING.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_processing_state_response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.PROCESSING.value
    assert order.processing_date == datetime(
        2024,
        5,
        8,
        10,
        18,
        0,
        tzinfo=timezone.utc,
    )
    mock_googlemaps_distance_matrix.assert_called_once()
    mock_stripe_payment_intent_create.assert_called_once()
    mock_stripe_create_refund_success.assert_not_called()

    with freeze_time("2024-05-08T10:20:00+00:00"):
        update_to_completed_state_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.COMPLETED.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_completed_state_response.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.COMPLETED.value
    assert order.completed_date == datetime(
        2024,
        5,
        8,
        10,
        20,
        0,
        tzinfo=timezone.utc,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_status",
    [
        OrderStatusEnum.PROCESSING,
        OrderStatusEnum.COMPLETED,
    ],
    ids=[
        "switch_to_processing",
        "switch_to_completed",
    ],
)
def test_update_order_but_unexpected_exception_raises_on_cooker_app(
    auth_headers: dict,
    client: APIClient,
    mock_transition_to: MagicMock,
    cookers_order_path: str,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_payment_intent_update: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
    mock_stripe_webhook_construct_event_failed: MagicMock,
    new_status: OrderStatusEnum,
) -> None:

    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_data_for_order_with_asap_delivery,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        order_id = response.json()["data"].pop("id")
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

        # Manually set the order to PENDING status
        order.status = OrderStatusEnum.PENDING.value
        order.save()

        # Now we try to set the order to another status but
        # an unexpected exception is raised
        update_response = client.patch(
            f"{cookers_order_path}{order_id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": new_status.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        mock_googlemaps_distance_matrix.assert_called_once()
        mock_stripe_payment_intent_create.assert_called_once()
        mock_stripe_webhook_construct_event_success.assert_not_called()
        mock_stripe_webhook_construct_event_failed.assert_not_called()
        mock_stripe_payment_intent_update.assert_not_called()
        mock_transition_to.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_status",
    [
        OrderStatusEnum.DELIVERED,
        OrderStatusEnum.CANCELLED_BY_COOKER,
    ],
    ids=[
        "switch_to_processing",
        "switch_to_cancelled_by_cooker",
    ],
)
def test_update_cooker_acceptance_rate(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
    cooker_id: int,
    new_status: OrderStatusEnum,
) -> None:

    # To start with a clean state we have to remove cookers orders
    # except the delivered ones

    OrderModel.objects.exclude(status=OrderStatusEnum.DELIVERED.value).delete()

    for order_item in OrderModel.objects.filter(cooker_id=cooker_id):
        assert order_item.status == OrderStatusEnum.DELIVERED.value

    cooker: CookerModel = CookerModel.objects.get(id=cooker_id)
    assert Decimal(str(cooker.acceptance_rate)) == Decimal("100.0")

    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            encode_multipart(
                BOUNDARY,
                post_order_data,
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")

        assert order.status == OrderStatusEnum.DRAFT.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        # Then we switch the order to pending few minutes later
        order.status = OrderStatusEnum.PENDING.value
        order.save()

    if new_status == OrderStatusEnum.DELIVERED:
        # Bypassing status update logic for simplicity
        order.status = OrderStatusEnum.COMPLETED.value
        order.save()

    with freeze_time("2024-05-08T10:41:00+00:00"):
        # Then we switch the order to the new_status
        update_status_data = {
            "status": new_status.value,
        }
        update_to_cancelled_by_cooker_response = client.patch(
            f"{cookers_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_cancelled_by_cooker_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

    if new_status == OrderStatusEnum.DELIVERED:
        assert Decimal(str(order.cooker.acceptance_rate)) == Decimal("100.0")

    if new_status == OrderStatusEnum.CANCELLED_BY_COOKER:
        assert Decimal(str(order.cooker.acceptance_rate)) == Decimal("90.0")

    assert order.cooker.last_acceptance_rate_update_date == datetime(
        2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc
    )

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )

    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        customer="cus_QyZ76Ae0W5KeqP",
    )

    if new_status == OrderStatusEnum.CANCELLED_BY_COOKER:
        mock_stripe_create_refund_success.assert_called_once_with(
            amount=2319,
            payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
        )
