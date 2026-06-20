from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from core_app.models import AddressModel, CookerModel, CustomerModel, OrderModel
from django.core.management import call_command
from freezegun import freeze_time
from utils.enums import OrderStatusEnum

BASE_FROZEN_TIME = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


def make_order(
    cooker: CookerModel,
    is_scheduled: bool = False,
    status: OrderStatusEnum = OrderStatusEnum.PENDING,
    stripe_payment_intent_id: str = "pi_test_123",
) -> OrderModel:
    return OrderModel.objects.create(
        cooker=cooker,
        customer=CustomerModel.objects.first(),
        address=AddressModel.objects.first(),
        status=status,
        is_scheduled=is_scheduled,
        delivery_fees=5.0,
        delivery_distance=1000.0,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_payment_intent_secret="cs_test_abc",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_scheduled,minutes_to_advance",
    [
        (False, 6),
        (True, 61),
    ],
    ids=["asap_past_5min_timeout", "scheduled_past_60min_timeout"],
)
def test_expired_order_transitions_to_not_accepted(
    is_scheduled: bool,
    minutes_to_advance: int,
    mock_stripe_payment_intent_cancel: MagicMock,
) -> None:
    with freeze_time(BASE_FROZEN_TIME) as frozen_time:
        OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()
        cooker = CookerModel.objects.get(pk=1)
        order = make_order(cooker, is_scheduled=is_scheduled)
        frozen_time.move_to(BASE_FROZEN_TIME + timedelta(minutes=minutes_to_advance))
        call_command("expire_pending_orders")

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.NOT_ACCEPTED.value
    mock_stripe_payment_intent_cancel.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_scheduled,minutes_to_advance",
    [
        (False, 3),
        (True, 30),
        (True, 6),
    ],
    ids=[
        "asap_3min_within_5min_timeout",
        "scheduled_30min_within_60min_timeout",
        "scheduled_6min_asap_timeout_does_not_apply",
    ],
)
def test_order_not_yet_expired_is_not_touched(
    is_scheduled: bool,
    minutes_to_advance: int,
    mock_stripe_payment_intent_cancel: MagicMock,
) -> None:
    with freeze_time(BASE_FROZEN_TIME) as frozen_time:
        OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()
        cooker = CookerModel.objects.get(pk=1)
        order = make_order(cooker, is_scheduled=is_scheduled)
        frozen_time.move_to(BASE_FROZEN_TIME + timedelta(minutes=minutes_to_advance))
        call_command("expire_pending_orders")

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.PENDING.value
    mock_stripe_payment_intent_cancel.assert_not_called()


@pytest.mark.django_db
def test_expired_order_cancels_stripe_authorization(
    mock_stripe_payment_intent_cancel: MagicMock,
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    # A pending order is only authorized, never captured: we cancel the
    # authorization and must NOT attempt a refund (which would fail on Stripe).
    with freeze_time(BASE_FROZEN_TIME) as frozen_time:
        OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()
        cooker = CookerModel.objects.get(pk=1)
        make_order(cooker, is_scheduled=False, stripe_payment_intent_id="pi_test_cancel")
        frozen_time.move_to(BASE_FROZEN_TIME + timedelta(minutes=6))
        call_command("expire_pending_orders")

    mock_stripe_payment_intent_cancel.assert_called_once_with("pi_test_cancel")
    mock_stripe_create_refund_success.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_rate,expected_rate",
    [
        (80.0, 70.0),
        (5.0, 0.0),
    ],
    ids=["normal_decrease", "floor_at_zero"],
)
def test_expired_order_updates_acceptance_rate(
    initial_rate: float,
    expected_rate: float,
    mock_stripe_payment_intent_cancel: MagicMock,
) -> None:
    with freeze_time(BASE_FROZEN_TIME) as frozen_time:
        OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()
        cooker = CookerModel.objects.get(pk=1)
        cooker.acceptance_rate = initial_rate
        cooker.save()
        make_order(cooker, is_scheduled=False)
        frozen_time.move_to(BASE_FROZEN_TIME + timedelta(minutes=6))
        call_command("expire_pending_orders")

    cooker.refresh_from_db()
    assert cooker.acceptance_rate == expected_rate
    mock_stripe_payment_intent_cancel.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "non_pending_status",
    [
        OrderStatusEnum.ACCEPTED,
        OrderStatusEnum.PREPARING,
        OrderStatusEnum.READY,
        OrderStatusEnum.DELIVERING,
        OrderStatusEnum.COMPLETED,
        OrderStatusEnum.CANCELLED,
    ],
    ids=["accepted", "preparing", "ready", "delivering", "completed", "cancelled"],
)
def test_non_pending_orders_are_never_expired(
    non_pending_status: OrderStatusEnum,
    mock_stripe_payment_intent_cancel: MagicMock,
) -> None:
    with freeze_time(BASE_FROZEN_TIME) as frozen_time:
        OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()
        cooker = CookerModel.objects.get(pk=1)
        make_order(
            cooker,
            status=non_pending_status,
            stripe_payment_intent_id=f"pi_test_{non_pending_status.value}",
        )
        frozen_time.move_to(BASE_FROZEN_TIME + timedelta(minutes=6))
        call_command("expire_pending_orders")

    mock_stripe_payment_intent_cancel.assert_not_called()
