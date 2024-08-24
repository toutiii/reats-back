import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from customer_app.models import OrderModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


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
