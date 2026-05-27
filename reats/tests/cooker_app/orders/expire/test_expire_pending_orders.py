from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from core_app.models import AddressModel, CookerModel, CustomerModel, OrderModel
from django.core.management import call_command
from freezegun import freeze_time
from utils.enums import OrderStatusEnum

# flake8: noqa: E501


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pending_order(cooker: CookerModel, is_scheduled: bool, created_at: datetime) -> OrderModel:
    order = OrderModel.objects.create(
        cooker=cooker,
        customer=CustomerModel.objects.first(),
        address=AddressModel.objects.first(),
        status=OrderStatusEnum.PENDING,
        is_scheduled=is_scheduled,
        delivery_fees=5.0,
        delivery_distance=1000.0,
        stripe_payment_intent_id="pi_test_123",
        stripe_payment_intent_secret="cs_test_abc",
    )
    OrderModel.objects.filter(pk=order.pk).update(created=created_at)
    order.refresh_from_db()
    return order


# ---------------------------------------------------------------------------
# Expired orders → transition to NOT_ACCEPTED
# Parametrized: same assertion, two different timeout rules
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_scheduled,frozen_time,created_at",
    [
        # ASAP: 6 min elapsed, timeout = 5 min
        (False, "2024-06-01T10:10:00+00:00", datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)),
        # Scheduled: 61 min elapsed, timeout = 60 min
        (True, "2024-06-01T12:00:00+00:00", datetime(2024, 6, 1, 10, 59, 0, tzinfo=timezone.utc)),
    ],
)
def test_expired_order_transitions_to_not_accepted(
    is_scheduled: bool,
    frozen_time: str,
    created_at: datetime,
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    order = make_pending_order(cooker, is_scheduled=is_scheduled, created_at=created_at)

    with freeze_time(frozen_time):
        call_command("expire_pending_orders")

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.NOT_ACCEPTED.value


# ---------------------------------------------------------------------------
# Orders not yet expired → must remain PENDING, no refund
# Parametrized: same assertions, three different "within timeout" scenarios
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_scheduled,frozen_time,created_at",
    [
        # ASAP: 3 min elapsed, timeout = 5 min → not expired
        (False, "2024-06-01T10:10:00+00:00", datetime(2024, 6, 1, 10, 7, 0, tzinfo=timezone.utc)),
        # Scheduled: 30 min elapsed, timeout = 60 min → not expired
        (True, "2024-06-01T12:00:00+00:00", datetime(2024, 6, 1, 11, 30, 0, tzinfo=timezone.utc)),
        # Scheduled: 6 min elapsed, past ASAP timeout but ASAP rule doesn't apply → not expired
        (True, "2024-06-01T10:10:00+00:00", datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)),
    ],
)
def test_order_not_yet_expired_is_not_touched(
    is_scheduled: bool,
    frozen_time: str,
    created_at: datetime,
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    order = make_pending_order(cooker, is_scheduled=is_scheduled, created_at=created_at)

    with freeze_time(frozen_time):
        call_command("expire_pending_orders")

    order.refresh_from_db()
    assert order.status == OrderStatusEnum.PENDING.value
    mock_stripe_create_refund_success.assert_not_called()


# ---------------------------------------------------------------------------
# Side-effects of expiry: Stripe refund and acceptance_rate penalty
# Kept separate — each verifies a distinct effect of the same scenario
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@freeze_time("2024-06-01T10:10:00+00:00")
def test_expired_order_triggers_stripe_refund(
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    created_at = datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)
    make_pending_order(cooker, is_scheduled=False, created_at=created_at)

    call_command("expire_pending_orders")

    mock_stripe_create_refund_success.assert_called_once()


@pytest.mark.django_db
@freeze_time("2024-06-01T10:10:00+00:00")
def test_expired_order_decreases_acceptance_rate(
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    initial_rate = Decimal(str(cooker.acceptance_rate))
    created_at = datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)
    make_pending_order(cooker, is_scheduled=False, created_at=created_at)

    call_command("expire_pending_orders")

    cooker.refresh_from_db()
    assert Decimal(str(cooker.acceptance_rate)) == initial_rate - Decimal("10")


# ---------------------------------------------------------------------------
# Non-pending orders are never touched
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@freeze_time("2024-06-01T10:10:00+00:00")
@pytest.mark.parametrize(
    "non_pending_status",
    [
        OrderStatusEnum.ACCEPTED,
        OrderStatusEnum.PREPARING,
        OrderStatusEnum.COMPLETED,
        OrderStatusEnum.CANCELLED,
    ],
)
def test_non_pending_orders_are_never_expired(
    non_pending_status: OrderStatusEnum,
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    created_at = datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)

    order = OrderModel.objects.create(
        cooker=cooker,
        customer=CustomerModel.objects.first(),
        address=AddressModel.objects.first(),
        status=non_pending_status,
        is_scheduled=False,
        delivery_fees=5.0,
        delivery_distance=1000.0,
        stripe_payment_intent_id=f"pi_test_{non_pending_status.value}",
        stripe_payment_intent_secret="cs_test_abc",
    )
    OrderModel.objects.filter(pk=order.pk).update(created=created_at)

    call_command("expire_pending_orders")

    mock_stripe_create_refund_success.assert_not_called()


# ---------------------------------------------------------------------------
# acceptance_rate floor: cannot go below 0
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@freeze_time("2024-06-01T10:10:00+00:00")
def test_acceptance_rate_does_not_go_below_zero(
    mock_stripe_create_refund_success: MagicMock,
) -> None:
    OrderModel.objects.filter(status=OrderStatusEnum.PENDING).delete()

    cooker = CookerModel.objects.get(pk=1)
    cooker.acceptance_rate = 5.0
    cooker.save()

    created_at = datetime(2024, 6, 1, 10, 4, 0, tzinfo=timezone.utc)
    make_pending_order(cooker, is_scheduled=False, created_at=created_at)

    call_command("expire_pending_orders")

    cooker.refresh_from_db()
    assert cooker.acceptance_rate == 0.0
