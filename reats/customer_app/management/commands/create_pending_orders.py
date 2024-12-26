import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from cooker_app.models import DishModel, DrinkModel
from customer_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    OrderItemModel,
    OrderModel,
)
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from utils.enums import OrderStatusEnum


class Command(BaseCommand):
    help = "Generate pending orders for development purposes."

    def _generate_mock_payment_intent(self):
        return {
            "id": f"pi_{uuid.uuid4().hex[:20]}",
            "client_secret": f"cs_{uuid.uuid4().hex[:25]}",
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=5, help="Number of pending orders to create"
        )

    def handle(self, *args, **options):
        if not self.check_local_environment():
            self.stderr.write(
                "This command can only be run in a local development environment."
            )
            return

        count = options["count"]
        cooker_id = 1  # Change if needed
        customer_id = 1  # Change if needed
        address_id = 3  # Change if needed

        cooker: CookerModel = CookerModel.objects.get(pk=cooker_id)
        assert cooker.is_activated, "Cooker must be activated."

        customer: CustomerModel = CustomerModel.objects.get(pk=customer_id)
        assert customer.is_activated, "Customer must be activated."

        address: AddressModel = AddressModel.objects.get(pk=address_id)

        dishes = list(DishModel.objects.filter(cooker=cooker, is_enabled=True))
        drinks = list(DrinkModel.objects.filter(cooker=cooker, is_enabled=True))

        if not dishes or not drinks:
            self.stderr.write("No enabled dishes or drinks found for the cooker.")
            return

        for _ in range(count):
            payment_intent = self._generate_mock_payment_intent()

            order: OrderModel = OrderModel.objects.create(
                cooker=cooker,
                customer=customer,
                address=address,
                scheduled_delivery_date=now() + timedelta(days=random.randint(1, 7)),
                is_scheduled=random.choice([True, False]),
                status=OrderStatusEnum.PENDING,
                delivery_fees=random.uniform(5.0, 20.0),
                delivery_distance=random.uniform(1.0, 10.0),
                stripe_payment_intent_id=payment_intent["id"],
                stripe_payment_intent_secret=payment_intent["client_secret"],
                created=datetime.now(timezone.utc),
            )

            # Add unique order items
            num_dishes = min(len(dishes), random.randint(1, 3))  # Up to 3 unique dishes
            selected_dishes = random.sample(dishes, num_dishes)
            for dish in selected_dishes:
                OrderItemModel.objects.create(
                    order=order,
                    dish=dish,
                    dish_quantity=random.randint(1, 3),  # 1 to 5 units of each dish
                )

            num_drinks = min(len(drinks), random.randint(1, 2))  # Up to 2 unique drinks
            selected_drinks = random.sample(drinks, num_drinks)
            for drink in selected_drinks:
                OrderItemModel.objects.create(
                    order=order,
                    drink=drink,
                    drink_quantity=random.randint(1, 3),  # 1 to 3 units of each drink
                )

            self.stdout.write(f"Created pending order with unique items: {order.id}")

    def check_local_environment(self):
        from django.conf import settings

        return settings.DEBUG and os.getenv("ENV") not in ["dev", "staging", "prod"]
