from datetime import timedelta
from decimal import Decimal

from core_app.models import OrderModel
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.timezone import now
from utils.common import compute_order_items_total_amount, create_stripe_refund, update_cooker_acceptance_rate
from utils.enums import OrderStatusEnum


class Command(BaseCommand):
    help = (
        "Expire pending orders that have exceeded the acceptance timeout. "
        "Transitions them to NOT_ACCEPTED, triggers a Stripe refund, and updates the cooker acceptance rate. "
    )

    def handle(self, *args, **kwargs) -> None:
        current_time = now()

        asap_cutoff = current_time - timedelta(minutes=settings.IDLE_CANCEL_TIME_FOR_ASAP_DELIVERY)
        scheduled_cutoff = current_time - timedelta(minutes=settings.IDLE_CANCEL_TIME_FOR_SCHEDULED_DELIVERY)

        expired_orders = OrderModel.objects.filter(
            status=OrderStatusEnum.PENDING,
        ).filter(Q(is_scheduled=False, created__lt=asap_cutoff) | Q(is_scheduled=True, created__lt=scheduled_cutoff))

        count = 0
        for order in expired_orders:
            try:
                order.transition_to(OrderStatusEnum.NOT_ACCEPTED)

                amount_to_refund_in_cents = Decimal(
                    str(compute_order_items_total_amount(order) + order.delivery_fees)
                ) * Decimal("100")
                create_stripe_refund(int(amount_to_refund_in_cents), order.stripe_payment_intent_id)

                update_cooker_acceptance_rate(order, OrderStatusEnum.NOT_ACCEPTED)

                count += 1
                self.stdout.write(f"Order {order.id} expired → not_accepted (cooker {order.cooker.id})")
            except Exception as e:
                self.stderr.write(f"Failed to expire order {order.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Done — {count} order(s) expired."))
