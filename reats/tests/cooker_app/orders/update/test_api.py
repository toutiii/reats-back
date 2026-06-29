from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from core_app.models import AddressModel, CookerModel, CustomerModel, OrderModel
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import CancelledByEnum, OrderStatusEnum

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
        "dishes_items": [
            {"dishID": "11", "dishOrderedQuantity": 1},
        ],
        "drinks_items": [
            {"drinkID": "2", "drinkOrderedQuantity": 3},
        ],
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
    mock_stripe_payment_intent_cancel: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")
        assert order.status == OrderStatusEnum.DRAFT.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        order.status = OrderStatusEnum.PENDING.value
        order.save()

    with freeze_time("2024-05-08T10:41:00+00:00"):
        response = client.post(
            f"{cookers_order_path}{order.id}/cancel/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

        assert order.status == OrderStatusEnum.CANCELLED.value
        assert order.cancelled_date == datetime(2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc)
        assert order

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_payment_intent_cancel.assert_called_once_with("pi_3Q6VU7EEYeaFww1W0xCZEUxw")
    mock_stripe_create_refund_success.assert_not_called()
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        capture_method="manual",
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
            post_order_data,
            format="json",
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
        response = client.post(
            f"{cookers_order_path}{order.id}/accept/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.ACCEPTED.value
    assert order.accepted_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)

    with freeze_time("2024-05-08T10:20:00+00:00"):
        response = client.post(
            f"{cookers_order_path}{order.id}/cancel/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.CANCELLED.value
    assert order.cancelled_date == datetime(2024, 5, 8, 10, 20, 0, tzinfo=timezone.utc)
    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_create_refund_success.assert_called_once_with(
        amount=2459,
        payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
    )
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        capture_method="manual",
        customer="cus_QyZ76Ae0W5KeqP",
    )


@pytest.mark.django_db
def test_update_order_from_preparing_to_cancelled_by_cooker_status(
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
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")
        assert order.status == OrderStatusEnum.DRAFT.value

    order.status = OrderStatusEnum.PENDING.value
    order.save()

    with freeze_time("2024-05-08T10:18:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/accept/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    with freeze_time("2024-05-08T10:19:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/start-preparation/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.PREPARING.value

    with freeze_time("2024-05-08T10:25:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/cancel/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.CANCELLED.value
    assert order.cancelled_by == CancelledByEnum.COOKER.value
    mock_stripe_create_refund_success.assert_called_once_with(
        amount=2459,
        payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
    )


@pytest.mark.django_db
def test_update_order_from_ready_to_cancelled_by_cooker_status(
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
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")
        assert order.status == OrderStatusEnum.DRAFT.value

    order.status = OrderStatusEnum.PENDING.value
    order.save()

    with freeze_time("2024-05-08T10:18:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/accept/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    with freeze_time("2024-05-08T10:19:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/start-preparation/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    with freeze_time("2024-05-08T10:30:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/mark-ready/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.READY.value

    with freeze_time("2024-05-08T10:35:00+00:00"):
        response = client.post(f"{cookers_order_path}{order.id}/cancel/", follow=False, **auth_headers)
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.CANCELLED.value
    assert order.cancelled_by == CancelledByEnum.COOKER.value
    mock_stripe_create_refund_success.assert_called_once_with(
        amount=2459,
        payment_intent="pi_3Q6VU7EEYeaFww1W0xCZEUxw",
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
    mock_stripe_payment_intent_capture: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")
        assert order.status == OrderStatusEnum.DRAFT.value

    order.status = OrderStatusEnum.PENDING.value
    order.save()

    with freeze_time("2024-05-08T10:18:00+00:00"):
        response = client.post(
            f"{cookers_order_path}{order.id}/accept/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.ACCEPTED.value
    assert order.accepted_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)
    mock_googlemaps_distance_matrix.assert_called_once()
    mock_stripe_payment_intent_create.assert_called_once()
    mock_stripe_create_refund_success.assert_not_called()
    # Manual capture: accepting the order is what actually charges the customer.
    mock_stripe_payment_intent_capture.assert_called_once_with(order.stripe_payment_intent_id)


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
            post_order_data,
            format="json",
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
        response = client.post(
            f"{cookers_order_path}{order.id}/accept/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == OrderStatusEnum.ACCEPTED.value
    assert order.accepted_date == datetime(2024, 5, 8, 10, 18, 0, tzinfo=timezone.utc)
    mock_googlemaps_distance_matrix.assert_called_once()
    mock_stripe_payment_intent_create.assert_called_once()
    mock_stripe_create_refund_success.assert_not_called()

    with freeze_time("2024-05-08T10:19:00+00:00"):
        res = client.post(f"{cookers_order_path}{order.id}/start-preparation/", **auth_headers)
        assert res.status_code == status.HTTP_200_OK

        res = client.post(f"{cookers_order_path}{order.id}/mark-ready/", **auth_headers)
        assert res.status_code == status.HTTP_200_OK

    # READY → DELIVERING and DELIVERING → COMPLETED are handled by the delivery app
    with freeze_time("2024-05-08T10:19:30+00:00"):
        order.refresh_from_db()
        order.status = OrderStatusEnum.DELIVERING.value
        order.delivering_date = datetime(2024, 5, 8, 10, 19, 30, tzinfo=timezone.utc)
        order.save()

    with freeze_time("2024-05-08T10:20:00+00:00"):
        order.status = OrderStatusEnum.COMPLETED.value
        order.completed_date = datetime(2024, 5, 8, 10, 20, 0, tzinfo=timezone.utc)
        order.save()

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.COMPLETED.value
    assert order.completed_date == datetime(2024, 5, 8, 10, 20, 0, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_update_order_with_invalid_transition_returns_400_validation_error(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        # First we create a draft order
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
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
        # Try to call start-preparation on a PENDING order (requires ACCEPTED first)
        invalid_transition_response = client.post(
            f"{cookers_order_path}{order.id}/start-preparation/",
            follow=False,
            **auth_headers,
        )

        # Should return 409 Conflict
        assert invalid_transition_response.status_code == status.HTTP_409_CONFLICT
        response_data = invalid_transition_response.json()
        assert "Cannot transition from PendingState to PreparingState" in response_data["error"]["message"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action_url",
    ["accept", "cancel"],
    ids=["accept", "cancel"],
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
    action_url: str,
) -> None:
    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            post_data_for_order_with_asap_delivery,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        order_id = response.json()["data"].pop("id")
        order: OrderModel = OrderModel.objects.get(id=order_id)

        assert order.status == OrderStatusEnum.DRAFT.value

        order.status = OrderStatusEnum.PENDING.value
        order.save()

        update_response = client.post(
            f"{cookers_order_path}{order_id}/{action_url}/",
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
def test_update_cooker_acceptance_rate_on_cancel(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    customer_order_path: str,
    post_order_data: dict,
    mock_googlemaps_distance_matrix: MagicMock,
    mock_stripe_payment_intent_create: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
    mock_stripe_payment_intent_cancel: MagicMock,
    cooker_id: int,
) -> None:
    OrderModel.objects.exclude(status=OrderStatusEnum.COMPLETED.value).delete()

    for order_item in OrderModel.objects.filter(cooker_id=cooker_id):
        assert order_item.status == OrderStatusEnum.COMPLETED.value

    cooker: CookerModel = CookerModel.objects.get(id=cooker_id)
    assert Decimal(str(cooker.acceptance_rate)) == Decimal("100.0")

    with freeze_time("2024-05-08T10:16:00+00:00"):
        response = client.post(
            customer_order_path,
            post_order_data,
            format="json",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

        order: OrderModel = OrderModel.objects.latest("pk")
        assert order.status == OrderStatusEnum.DRAFT.value

    with freeze_time("2024-05-08T10:18:00+00:00"):
        order.status = OrderStatusEnum.PENDING.value
        order.save()

    with freeze_time("2024-05-08T10:41:00+00:00"):
        update_response = client.post(
            f"{cookers_order_path}{order.id}/cancel/",
            follow=False,
            **auth_headers,
        )
        assert update_response.status_code == status.HTTP_200_OK

        order.refresh_from_db()

    assert Decimal(str(order.cooker.acceptance_rate)) == Decimal("90.0")
    assert order.cooker.last_acceptance_rate_update_date == datetime(2024, 5, 8, 10, 41, 0, tzinfo=timezone.utc)

    mock_googlemaps_distance_matrix.assert_called_once_with(
        origins=["13 rue des Mazières 91000 Evry"],
        destinations=["1 rue André Lalande 91000 Evry"],
    )
    mock_stripe_payment_intent_create.assert_called_once_with(
        amount=2459,
        currency="EUR",
        automatic_payment_methods={"enabled": True},
        capture_method="manual",
        customer="cus_QyZ76Ae0W5KeqP",
    )
    mock_stripe_payment_intent_cancel.assert_called_once_with("pi_3Q6VU7EEYeaFww1W0xCZEUxw")
    mock_stripe_create_refund_success.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatusEnum.PENDING,
        OrderStatusEnum.ACCEPTED,
        OrderStatusEnum.COMPLETED,
        OrderStatusEnum.DELIVERING,
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.COMPLETED,
    ],
    ids=[
        s.value
        for s in [
            OrderStatusEnum.PENDING,
            OrderStatusEnum.ACCEPTED,
            OrderStatusEnum.COMPLETED,
            OrderStatusEnum.DELIVERING,
            OrderStatusEnum.CANCELLED,
            OrderStatusEnum.CANCELLED,
            OrderStatusEnum.COMPLETED,
        ]
    ],
)
def test_update_order_of_another_cooker_returns_404(
    auth_headers: dict,
    client: APIClient,
    cookers_order_path: str,
    order_status: OrderStatusEnum,
) -> None:
    other_cooker = CookerModel.objects.exclude(id=1).first()
    assert other_cooker is not None, "Need at least another cooker in the DB"

    order = OrderModel.objects.create(
        cooker=other_cooker,
        customer=CustomerModel.objects.first(),
        address=AddressModel.objects.first(),
        status=order_status.value,
        delivery_distance=1.0,
        delivery_fees=2.0,
    )

    update_response = client.post(
        f"{cookers_order_path}{order.id}/accept/",
        **auth_headers,
    )

    assert update_response.status_code == status.HTTP_404_NOT_FOUND
