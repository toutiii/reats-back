import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest
from customer_app.models import OrderItemModel, OrderModel
from django.forms import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

# Add this line to ignore E501 errors
# flake8: noqa: E501


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def address_id() -> int:
    return 2


@pytest.fixture
def post_order_data(
    address_id: int,
    customer_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
        "deliveryPlanning": "asap",
    }


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_cancelled_by_customer(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
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

        assert order.status == "draft"

    with freeze_time("2024-05-08T10:18:00+00:00"):
        # Then we switch the order to pending few minutes later
        update_status_data: dict = {"status": "pending"}
        update_to_pending_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_pending_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "pending"
        assert order.paid_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)

    with freeze_time("2024-05-08T10:41:00+00:00"):
        # Then we switch the order to cancelled by customer few minutes later
        update_status_data = {"status": "cancelled_by_customer"}
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

        assert order.status == "cancelled_by_customer"
        assert order.cancelled_date == datetime(
            2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc
        )
        assert order

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_cancelled_by_cooker(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
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

        assert order.status == "draft"

    with freeze_time("2024-05-08T10:18:00+00:00"):
        # Then we switch the order to pending few minutes later
        update_status_data: dict = {"status": "pending"}
        update_to_pending_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_pending_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "pending"
        assert order.paid_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)

    with freeze_time("2024-05-08T10:41:00+00:00"):
        # Then we switch the order to cancelled by cooker few minutes later
        update_status_data = {"status": "cancelled_by_cooker"}
        update_to_cancelled_by_cooker_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_cancelled_by_cooker_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "cancelled_by_cooker"
        assert order.cancelled_date == datetime(
            2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc
        )

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )


@pytest.mark.django_db
def test_switch_order_status_from_draft_to_delivered(
    auth_headers: dict,
    client: APIClient,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
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

        assert order.status == "draft"

    with freeze_time("2024-05-08T10:18:00+00:00"):
        # Then we switch the order to pending few minutes later
        update_status_data: dict = {"status": "pending"}
        update_to_pending_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_pending_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "pending"
        assert order.paid_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)

    with freeze_time("2024-05-08T10:30:00+00:00"):
        # Then we switch the order to processing few minutes later
        update_status_data = {"status": "processing"}
        update_to_processing_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_processing_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "processing"
        assert order.processing_date == datetime(
            2024, 5, 8, 10, 30, 0, tzinfo=timezone.utc
        )

    with freeze_time("2024-05-08T10:32:00+00:00"):
        # Then we switch the order to completed few minutes later
        update_status_data = {"status": "completed"}
        update_to_completed_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_completed_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "completed"
        assert order.completed_date == datetime(
            2024, 5, 8, 10, 32, 0, tzinfo=timezone.utc
        )

    with freeze_time("2024-05-08T10:35:00+00:00"):
        # Then we switch the order to delivered few minutes later
        update_status_data = {"status": "delivered"}
        update_to_delivered_response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert update_to_delivered_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == "delivered"
        assert order.delivered_date == datetime(
            2024, 5, 8, 10, 35, 0, tzinfo=timezone.utc
        )

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
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
        "processing",
        "completed",
        "delivered",
        "cancelled_by_customer",
        "cancelled_by_cooker",
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
        update_status_data = {"status": "pending"}
        response = client.patch(
            f"{customer_order_path}{order.id}/",
            encode_multipart(BOUNDARY, update_status_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()

    non_allowed_statuses = ["draft", "delivered"]

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
        update_status_data = {"status": "pending"}
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
        update_status_data = {"status": "processing"}
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
        "draft",
        "pending",
        "cancelled_by_customer",
        "cancelled_by_cooker",
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
        update_status_data = {"status": "pending"}
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
        update_status_data = {"status": "processing"}
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
        update_status_data = {"status": "completed"}
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
        "draft",
        "pending",
        "processing",
        "cancelled_by_customer",
        "cancelled_by_cooker",
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
        update_status_data = {"status": "pending"}
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
        update_status_data = {"status": "processing"}
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
        update_status_data = {"status": "completed"}
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
        update_status_data = {"status": "delivered"}
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
        "draft",
        "pending",
        "processing",
        "completed",
        "cancelled_by_customer",
        "cancelled_by_cooker",
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
        update_status_data = {"status": "pending"}
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
        update_status_data = {"status": "cancelled_by_customer"}
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
        "draft",
        "pending",
        "processing",
        "completed",
        "delivered",
        "cancelled_by_cooker",
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
        update_status_data = {"status": "pending"}
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
        update_status_data = {"status": "cancelled_by_cooker"}
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
        "draft",
        "pending",
        "processing",
        "completed",
        "delivered",
        "cancelled_by_customer",
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
def post_data_for_order_with_asap_delivery(
    address_id: int,
    customer_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }


@pytest.fixture
def post_data_for_order_update(
    address_id: int,
    customer_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
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
            "status": "draft",
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
            "delivery_man": None,
            "scheduled_delivery_date": None,
            "is_scheduled": False,
            "status": "draft",
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

        assert order.status == "pending"

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

        assert order.status == "draft"

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
