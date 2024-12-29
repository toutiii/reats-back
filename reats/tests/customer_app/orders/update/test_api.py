import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest
from core_app.models import OrderItemModel, OrderModel
from django.forms import model_to_dict
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
def test_switch_order_status_from_draft_to_cancelled_by_customer(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
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
        # Then we switch the order to cancelled by customer few minutes later
        update_status_data = {
            "status": OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
        }
        update_to_cancelled_by_customer_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert (
            update_to_cancelled_by_customer_response.status_code == status.HTTP_200_OK
        )

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.CANCELLED_BY_CUSTOMER.value
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
    mock_stripe_create_ephemeral_key.assert_called_once_with(
        customer="cus_QyZ76Ae0W5KeqP",
        stripe_version="2024-06-20",
    )


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_cancelled_by_cooker(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
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
            f"{customer_order_path}{order.id}/",
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

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_not_called()
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        customer="cus_QyZ76Ae0W5KeqP",
    )
    mock_stripe_create_ephemeral_key.assert_called_once_with(
        customer="cus_QyZ76Ae0W5KeqP",
        stripe_version="2024-06-20",
    )


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_delivered(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
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

    with freeze_time("2024-05-08T10:30:00+00:00"):
        # Then we switch the order to processing few minutes later
        update_status_data = {
            "status": OrderStatusEnum.PROCESSING.value,
        }
        update_to_processing_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_processing_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.PROCESSING.value
        assert order.processing_date == datetime(
            2024, 5, 8, 10, 30, 0, tzinfo=timezone.utc
        )

    with freeze_time("2024-05-08T10:32:00+00:00"):
        # Then we switch the order to completed few minutes later
        update_status_data = {
            "status": OrderStatusEnum.COMPLETED.value,
        }
        update_to_completed_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_completed_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.COMPLETED.value
        assert order.completed_date == datetime(
            2024, 5, 8, 10, 32, 0, tzinfo=timezone.utc
        )

    with freeze_time("2024-05-08T10:35:00+00:00"):
        # Then we switch the order to delivered few minutes later
        update_status_data = {
            "status": OrderStatusEnum.DELIVERED.value,
        }
        update_to_delivered_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_delivered_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.DELIVERED.value
        assert order.delivered_date == datetime(
            2024, 5, 8, 10, 35, 0, tzinfo=timezone.utc
        )

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_not_called()
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        customer="cus_QyZ76Ae0W5KeqP",
    )
    mock_stripe_create_ephemeral_key.assert_called_once_with(
        customer="cus_QyZ76Ae0W5KeqP",
        stripe_version="2024-06-20",
    )


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    non_allowed_statuses = [
        OrderStatusEnum.PROCESSING.value,
        OrderStatusEnum.COMPLETED.value,
        OrderStatusEnum.DELIVERED.value,
        OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
        OrderStatusEnum.CANCELLED_BY_COOKER.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T10:41:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.mark.django_db
def test_switch_order_status_from_pending_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.COMPLETED.value,
        OrderStatusEnum.DELIVERED.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T10:41:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.mark.django_db
def test_switch_order_status_from_processing_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from pending to processing
    with freeze_time("2024-05-08T10:41:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PROCESSING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.PENDING.value,
        OrderStatusEnum.DELIVERED.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T10:55:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.mark.django_db
def test_switch_order_status_from_completed_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from pending to processing
    with freeze_time("2024-05-08T10:41:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PROCESSING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from processing to completed
    with freeze_time("2024-05-08T10:55:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.COMPLETED.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.PENDING.value,
        OrderStatusEnum.PROCESSING.value,
        OrderStatusEnum.CANCELLED_BY_COOKER.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T11:10:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.mark.django_db
def test_switch_order_status_from_delivered_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from pending to processing
    with freeze_time("2024-05-08T10:41:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PROCESSING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from processing to completed
    with freeze_time("2024-05-08T10:55:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.COMPLETED.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from completed to delivered
    with freeze_time("2024-05-08T11:10:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.DELIVERED.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.PENDING.value,
        OrderStatusEnum.PROCESSING.value,
        OrderStatusEnum.COMPLETED.value,
        OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
        OrderStatusEnum.CANCELLED_BY_COOKER.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T11:25:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.mark.django_db
def test_switch_order_status_from_cancelled_by_customer_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from pending to cancelled by customer
    with freeze_time("2024-05-08T11:10:00+00:00"):
        update_status_data = {
            "status": OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
        }
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.PENDING.value,
        OrderStatusEnum.PROCESSING.value,
        OrderStatusEnum.COMPLETED.value,
        OrderStatusEnum.DELIVERED.value,
        OrderStatusEnum.CANCELLED_BY_COOKER.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T11:25:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
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
    mock_stripe_create_ephemeral_key.assert_called_once_with(
        customer="cus_QyZ76Ae0W5KeqP",
        stripe_version="2024-06-20",
    )


@pytest.mark.django_db
def test_switch_order_status_from_cancelled_by_cooker_to_non_allowed_status(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # Create a draft order
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
        order = OrderModel.objects.latest("pk")

    # Transition from draft to pending
    with freeze_time("2024-05-08T10:18:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.PENDING.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    # Transition from pending to cancelled by cooker
    with freeze_time("2024-05-08T11:10:00+00:00"):
        update_status_data = {"status": OrderStatusEnum.CANCELLED_BY_COOKER.value}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = [
        OrderStatusEnum.DRAFT.value,
        OrderStatusEnum.PENDING.value,
        OrderStatusEnum.PROCESSING.value,
        OrderStatusEnum.COMPLETED.value,
        OrderStatusEnum.DELIVERED.value,
        OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
    ]

    for order_status in non_allowed_statuses:
        with freeze_time("2024-05-08T11:25:00+00:00"):
            update_status_data = {"status": order_status}
            response = client.patch(
                f"{customer_order_path}{order.id}/",
                encode_multipart(BOUNDARY, update_status_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            mock_googlemaps_distance_matrix.assert_called_once_with(
                origins=["13 rue des Mazières 91000 Evry"],
                destinations=["1 rue André Lalande 91000 Evry"],
            )


@pytest.fixture
def post_data_for_order_update(
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
                {"dishID": "5", "dishOrderedQuantity": 2},
                {"dishID": "6", "dishOrderedQuantity": 2},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
                {"drinkID": "1", "drinkOrderedQuantity": 2},
            ]
        ),
    }


@pytest.mark.django_db
def test_update_order_success_with_asap_delivery(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    post_data_for_order_update: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_payment_intent_update: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
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
        api_response = response.json()
        order_id = api_response["data"].pop("id")
        assert order_id is not None
        assert response.json() == {
            "ok": True,
            "status_code": 200,
            "data": {
                "items": [
                    {
                        "dish_quantity": 1,
                        "drink_quantity": None,
                        "dish": 11,
                        "drink": None,
                    },
                    {
                        "dish_quantity": None,
                        "drink_quantity": 3,
                        "dish": None,
                        "drink": 2,
                    },
                ],
                "scheduled_delivery_date": None,
                "is_scheduled": False,
                "processing_date": None,
                "completed_date": None,
                "delivery_in_progress_date": None,
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 3.19,
                "delivery_distance": 1390.0,
                "delivery_initial_distance": None,
                "paid_date": None,
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "address": 2,
                "delivery_man": None,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "sub_total": 20.0,
                "total_amount": 24.59,
                "service_fees": 1.4,
            },
        }
        last_order: OrderModel = OrderModel.objects.latest("pk")
        order_dict = model_to_dict(last_order)
        del order_dict["id"]

        assert order_dict == {
            "address": 2,
            "cancelled_date": None,
            "completed_date": None,
            "customer": 1,
            "cooker": 1,
            "delivered_date": None,
            "delivery_distance": 1390.0,
            "delivery_fees": 3.19,
            "delivery_fees_bonus": None,
            "delivery_in_progress_date": None,
            "delivery_initial_distance": None,
            "delivery_man": None,
            "paid_date": None,
            "is_scheduled": False,
            "processing_date": None,
            "scheduled_delivery_date": None,
            "status": OrderStatusEnum.DRAFT.value,
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }

        order_item_query = OrderItemModel.objects.filter(order__id=last_order.id)

        # Now we update the order with new items
        update_response = client.put(
            f"{customer_order_path}{last_order.id}/",
            encode_multipart(BOUNDARY, post_data_for_order_update),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert update_response.status_code == status.HTTP_200_OK
        update_response_order_id = update_response.json()["data"].pop("id")
        assert update_response_order_id == last_order.id
        assert update_response_order_id == last_order.id
        last_order.refresh_from_db()
        assert update_response.json() == {
            "data": {
                "address": 2,
                "cancelled_date": None,
                "completed_date": None,
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "delivered_date": None,
                "delivery_distance": 1390.0,
                "delivery_fees": 3.19,
                "delivery_in_progress_date": None,
                "delivery_initial_distance": None,
                "delivery_man": None,
                "is_scheduled": False,
                "items": [
                    {
                        "dish": 5,
                        "dish_quantity": 2,
                        "drink": None,
                        "drink_quantity": None,
                    },
                    {
                        "dish": 6,
                        "dish_quantity": 2,
                        "drink": None,
                        "drink_quantity": None,
                    },
                    {
                        "dish": None,
                        "dish_quantity": None,
                        "drink": 2,
                        "drink_quantity": 3,
                    },
                    {
                        "dish": None,
                        "dish_quantity": None,
                        "drink": 1,
                        "drink_quantity": 2,
                    },
                ],
                "paid_date": None,
                "processing_date": None,
                "scheduled_delivery_date": None,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "sub_total": 66.0,
                "total_amount": 73.81,
                "service_fees": 4.62,
            },
            "ok": True,
            "status_code": 200,
        }

        updated_order_dict = model_to_dict(last_order)
        del updated_order_dict["id"]
        assert updated_order_dict == {
            "customer": 1,
            "address": 2,
            "cooker": 1,
            "delivery_man": None,
            "scheduled_delivery_date": None,
            "is_scheduled": False,
            "status": OrderStatusEnum.DRAFT.value,
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
            "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
        }
        assert order_item_query.count() == 4

        for order_item in order_item_query:
            if order_item.dish:
                assert order_item.dish.id in [5, 6]
                assert order_item.dish_quantity == 2
            elif order_item.drink:
                if order_item.drink.id == 1:
                    assert order_item.drink_quantity == 2
                elif order_item.drink.id == 2:
                    assert order_item.drink_quantity == 3
            else:
                assert False, "An order item must be either a dish or a drink"

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
        mock_stripe_payment_intent_update.assert_called_once_with(
            "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
            amount=7381,
        )
        mock_stripe_create_ephemeral_key.assert_has_calls(
            [
                call(customer="cus_QyZ76Ae0W5KeqP", stripe_version="2024-06-20"),
                call(customer="cus_QyZ76Ae0W5KeqP", stripe_version="2024-06-20"),
            ]
        )


@pytest.mark.django_db
def test_update_order_after_successful_stripe_payment(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    stripe_payment_intent_success_webhook_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
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
        assert response.json() == {
            "ok": True,
            "status_code": 200,
            "data": {
                "items": [
                    {
                        "dish_quantity": 1,
                        "drink_quantity": None,
                        "dish": 11,
                        "drink": None,
                    },
                    {
                        "dish_quantity": None,
                        "drink_quantity": 3,
                        "dish": None,
                        "drink": 2,
                    },
                ],
                "scheduled_delivery_date": None,
                "is_scheduled": False,
                "processing_date": None,
                "completed_date": None,
                "delivery_in_progress_date": None,
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 3.19,
                "delivery_distance": 1390.0,
                "delivery_initial_distance": None,
                "paid_date": None,
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "address": 2,
                "delivery_man": None,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "sub_total": 20.0,
                "total_amount": 24.59,
                "service_fees": 1.4,
            },
        }

        # Then we post the payment intent success webhook
        response = client.post(
            "/api/v1/stripe/webhook/",
            json.dumps(stripe_payment_intent_success_webhook_data),
            follow=False,
        )

        assert response.status_code == status.HTTP_200_OK

        # Checking if the order has been updated to pending status
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.PENDING.value

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
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_QyZ76Ae0W5KeqP",
            stripe_version="2024-06-20",
        )
        mock_stripe_webhook_construct_event_success.assert_called_once()


@pytest.mark.django_db
def test_update_order_after_successful_stripe_payment_but_event_failed_to_be_verified(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    stripe_payment_intent_success_webhook_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_failed: MagicMock,
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
        assert response.json() == {
            "ok": True,
            "status_code": 200,
            "data": {
                "items": [
                    {
                        "dish_quantity": 1,
                        "drink_quantity": None,
                        "dish": 11,
                        "drink": None,
                    },
                    {
                        "dish_quantity": None,
                        "drink_quantity": 3,
                        "dish": None,
                        "drink": 2,
                    },
                ],
                "scheduled_delivery_date": None,
                "is_scheduled": False,
                "processing_date": None,
                "completed_date": None,
                "delivery_in_progress_date": None,
                "cancelled_date": None,
                "delivered_date": None,
                "delivery_fees": 3.19,
                "delivery_distance": 1390.0,
                "delivery_initial_distance": None,
                "paid_date": None,
                "customer": {
                    "firstname": "Ben",
                    "id": 1,
                    "lastname": "TEN",
                    "stripe_id": "cus_QyZ76Ae0W5KeqP",
                },
                "cooker": {
                    "firstname": "test",
                    "id": 1,
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
                "address": 2,
                "delivery_man": None,
                "stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "stripe_payment_intent_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "ephemeral_key": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp",
                "sub_total": 20.0,
                "total_amount": 24.59,
                "service_fees": 1.4,
            },
        }

        # Then we post the payment intent success webhook
        response = client.post(
            "/api/v1/stripe/webhook/",
            json.dumps(stripe_payment_intent_success_webhook_data),
            follow=False,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # The order is supposed to stay in draft status
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

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
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_QyZ76Ae0W5KeqP",
            stripe_version="2024-06-20",
        )
        mock_stripe_webhook_construct_event_failed.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "post_order_data, expected_cancel_response_status_code, cancel_freeze_time",
    [
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
            },
            status.HTTP_200_OK,
            "2024-11-10T08:45:00+00:00",
        ),
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
                "date": "11/15/2024",
                "time": "14:30:00",
            },
            status.HTTP_200_OK,
            "2024-11-10T09:25:00+00:00",
        ),
    ],
    ids=[
        "order with asap delivery is cancelled soon enough by customer",
        "order with scheduled delivery is cancelled soon enough by customer",
    ],
)
def test_cancel_order_when_initiated_by_customer_and_order_is_still_pending(
    auth_headers: dict,
    cancel_freeze_time: str,
    client: APIClient,
    customer_order_path: str,
    expected_cancel_response_status_code: int,
    post_order_data: dict,
    stripe_payment_intent_success_webhook_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
):
    with freeze_time("2024-11-10T08:16:00+00:00"):
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
        order_id = response.json()["data"].pop("id")
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

        # Then we post the payment intent success webhook
        stripe_payment_intent_success_webhook_data[
            "created"
        ] = datetime.now().timestamp()
        webhook_response = client.post(
            "/api/v1/stripe/webhook/",
            json.dumps(stripe_payment_intent_success_webhook_data),
            follow=False,
        )

        assert webhook_response.status_code == status.HTTP_200_OK

        # Checking if the order has been updated to pending status
        order.refresh_from_db()

        assert order.status == OrderStatusEnum.PENDING.value

        with freeze_time(cancel_freeze_time):
            # Now we cancel the order right after it has been paid
            cancel_response = client.patch(
                f"{customer_order_path}{order_id}/",
                encode_multipart(
                    BOUNDARY,
                    {
                        "status": OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
                    },
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert cancel_response.status_code == expected_cancel_response_status_code
            order.refresh_from_db()
            assert order.status == OrderStatusEnum.CANCELLED_BY_CUSTOMER.value
            assert order.cancelled_date == datetime.fromisoformat(cancel_freeze_time)

        mock_googlemaps_distance_matrix.assert_called_once_with(
            origins=["1 rue rené cassin résidence neptune 91100 Corbeil-Essonnes"],
            destinations=["1 rue André Lalande 91000 Evry"],
        )
        mock_stripe_payment_intent_create.assert_called_once_with(
            amount=2459,
            currency="EUR",
            automatic_payment_methods={"enabled": True},
            customer="cus_RBiuNyquyndC8O",
        )
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_RBiuNyquyndC8O",
            stripe_version="2024-06-20",
        )
        mock_stripe_webhook_construct_event_success.assert_called_once()
        mock_stripe_create_refund_success.assert_called_once_with(
            amount=2319,
            payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "post_order_data, expected_cancel_response_status_code, cancel_freeze_time",
    [
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
            },
            status.HTTP_200_OK,
            "2024-11-10T08:45:00+00:00",
        ),
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
                "date": "11/15/2024",
                "time": "14:30:00",
            },
            status.HTTP_200_OK,
            "2024-11-10T09:25:00+00:00",
        ),
    ],
    ids=[
        "order with asap delivery is cancelled but order is in processing state",
        "order with scheduled delivery is cancelled but order is in processing state",
    ],
)
def test_cancel_order_when_initiated_by_customer_but_order_is_in_processing_state(
    auth_headers: dict,
    cancel_freeze_time: str,
    client: APIClient,
    customer_order_path: str,
    expected_cancel_response_status_code: int,
    post_order_data: dict,
    stripe_payment_intent_success_webhook_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
):
    with freeze_time("2024-11-10T08:16:00+00:00"):
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
        order_id = response.json()["data"].pop("id")
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

        # Then we post the payment intent success webhook
        stripe_payment_intent_success_webhook_data[
            "created"
        ] = datetime.now().timestamp()
        webhook_response = client.post(
            "/api/v1/stripe/webhook/",
            json.dumps(stripe_payment_intent_success_webhook_data),
            follow=False,
        )

        assert webhook_response.status_code == status.HTTP_200_OK

        # Checking if the order has been updated to pending status
        order.refresh_from_db()

        assert order.status == OrderStatusEnum.PENDING.value

        # Manual transition from pending to processing
        order.status = OrderStatusEnum.PROCESSING.value
        order.save()

        assert order.status == OrderStatusEnum.PROCESSING.value

        with freeze_time(cancel_freeze_time):
            # Now we cancel the order right after it has been paid
            cancel_response = client.patch(
                f"{customer_order_path}{order_id}/",
                encode_multipart(
                    BOUNDARY,
                    {
                        "status": OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
                    },
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert cancel_response.status_code == expected_cancel_response_status_code
            order.refresh_from_db()
            assert order.status == OrderStatusEnum.CANCELLED_BY_CUSTOMER.value
            assert order.cancelled_date == datetime.fromisoformat(cancel_freeze_time)

        mock_googlemaps_distance_matrix.assert_called_once_with(
            origins=["1 rue rené cassin résidence neptune 91100 Corbeil-Essonnes"],
            destinations=["1 rue André Lalande 91000 Evry"],
        )
        mock_stripe_payment_intent_create.assert_called_once_with(
            amount=2459,
            currency="EUR",
            automatic_payment_methods={"enabled": True},
            customer="cus_RBiuNyquyndC8O",
        )
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_RBiuNyquyndC8O",
            stripe_version="2024-06-20",
        )
        mock_stripe_webhook_construct_event_success.assert_called_once()
        mock_stripe_create_refund_success.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "post_order_data, expected_cancel_response_status_code, cancel_freeze_time",
    [
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
            },
            status.HTTP_200_OK,
            "2024-11-10T08:45:00+00:00",
        ),
        (
            {
                "addressID": 1,
                "customerID": 2,
                "cookerID": 1,
                "items": json.dumps(
                    [
                        {"dishID": "11", "dishOrderedQuantity": 1},
                        {"drinkID": "2", "drinkOrderedQuantity": 3},
                    ]
                ),
                "date": "11/15/2024",
                "time": "14:30:00",
            },
            status.HTTP_200_OK,
            "2024-11-10T09:25:00+00:00",
        ),
    ],
    ids=[
        "order with asap delivery is cancelled but order is in completed state",
        "order with scheduled delivery is cancelled but order is in completed state",
    ],
)
def test_cancel_order_when_initiated_by_customer_but_order_is_in_completed_state(
    auth_headers: dict,
    cancel_freeze_time: str,
    client: APIClient,
    customer_order_path: str,
    expected_cancel_response_status_code: int,
    post_order_data: dict,
    stripe_payment_intent_success_webhook_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
):
    with freeze_time("2024-11-10T08:16:00+00:00"):
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
        order_id = response.json()["data"].pop("id")
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

        # Then we post the payment intent success webhook
        stripe_payment_intent_success_webhook_data[
            "created"
        ] = datetime.now().timestamp()
        webhook_response = client.post(
            "/api/v1/stripe/webhook/",
            json.dumps(stripe_payment_intent_success_webhook_data),
            follow=False,
        )

        assert webhook_response.status_code == status.HTTP_200_OK

        # Checking if the order has been updated to pending status
        order.refresh_from_db()

        assert order.status == OrderStatusEnum.PENDING.value

        # Manual transition from pending to processing
        order.status = OrderStatusEnum.PROCESSING.value
        order.save()

        assert order.status == OrderStatusEnum.PROCESSING.value

        # Then we switch the order to completed
        order.status = OrderStatusEnum.COMPLETED.value
        order.save()

        assert order.status == OrderStatusEnum.COMPLETED.value

        with freeze_time(cancel_freeze_time):
            # Now we cancel the order right after it has been paid
            cancel_response = client.patch(
                f"{customer_order_path}{order_id}/",
                encode_multipart(
                    BOUNDARY,
                    {
                        "status": OrderStatusEnum.CANCELLED_BY_CUSTOMER.value,
                    },
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert cancel_response.status_code == expected_cancel_response_status_code
            order.refresh_from_db()
            assert order.status == OrderStatusEnum.CANCELLED_BY_CUSTOMER.value
            assert order.cancelled_date == datetime.fromisoformat(cancel_freeze_time)

        mock_googlemaps_distance_matrix.assert_called_once_with(
            origins=["1 rue rené cassin résidence neptune 91100 Corbeil-Essonnes"],
            destinations=["1 rue André Lalande 91000 Evry"],
        )
        mock_stripe_payment_intent_create.assert_called_once_with(
            amount=2459,
            currency="EUR",
            automatic_payment_methods={"enabled": True},
            customer="cus_RBiuNyquyndC8O",
        )
        mock_stripe_create_ephemeral_key.assert_called_once_with(
            customer="cus_RBiuNyquyndC8O",
            stripe_version="2024-06-20",
        )
        mock_stripe_webhook_construct_event_success.assert_called_once()
        mock_stripe_create_refund_success.assert_not_called()


@pytest.mark.django_db
def test_update_order_but_unexpected_exception_raises_on_customer_app(
    auth_headers: dict,
    client: APIClient,
    mock_transition_to: MagicMock,
    customer_order_path: str,
    post_data_for_order_with_asap_delivery: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_payment_intent_update: MagicMock,
    mock_stripe_create_ephemeral_key: MagicMock,
    mock_stripe_webhook_construct_event_success: MagicMock,
    mock_stripe_webhook_construct_event_failed: MagicMock,
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

        # Now we try to set the order to PENDING status but
        # an unexpected exception is raised
        update_response = client.patch(
            f"{customer_order_path}{order_id}/",
            encode_multipart(
                BOUNDARY,
                {
                    "status": OrderStatusEnum.PENDING.value,
                },
            ),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        mock_googlemaps_distance_matrix.assert_called_once()
        mock_stripe_payment_intent_create.assert_called_once()
        mock_stripe_create_ephemeral_key.assert_called_once()
        mock_stripe_webhook_construct_event_success.assert_not_called()
        mock_stripe_webhook_construct_event_failed.assert_not_called()
        mock_stripe_payment_intent_update.assert_not_called()
        mock_transition_to.assert_called_once()
