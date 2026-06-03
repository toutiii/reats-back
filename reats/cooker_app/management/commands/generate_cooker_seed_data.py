import random
from datetime import datetime, timedelta, timezone

from core_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    DishModel,
    DrinkModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from utils.enums import CancelledByEnum, OrderStatusEnum


class Command(BaseCommand):
    help = "Generates 100 dummy orders per cooker (id=4 and id=1) to help frontend development."

    def add_arguments(self, parser):
        parser.add_argument(
            "-reset",
            action="store_true",
            help="Delete all existing orders for the default cooker before generating new ones",
        )

    def handle(self, *args, **options):
        # Priority cookers: id=4 first, id=1 second — 50 orders each
        cooker_4 = CookerModel.objects.filter(id=4).first()
        cooker_1 = CookerModel.objects.filter(id=1).first()
        target_cookers = [c for c in [cooker_4, cooker_1] if c is not None]
        if not target_cookers:
            self.stdout.write(self.style.ERROR("Neither cooker id=4 nor id=1 found. Please load fixtures."))
            return

        if options["reset"]:
            self.stdout.write("Deleting existing orders for target cookers...")
            OrderModel.objects.filter(cooker__in=target_cookers).delete()

        customers = list(CustomerModel.objects.all())
        addresses = list(AddressModel.objects.all())
        dishes_by_cooker = {c.id: list(DishModel.objects.filter(cooker=c)) for c in target_cookers}
        drinks_by_cooker = {c.id: list(DrinkModel.objects.filter(cooker=c)) for c in target_cookers}

        if not customers or not addresses:
            self.stdout.write(self.style.ERROR("Customers or addresses missing. Please load fixtures."))
            return

        distribution = {
            OrderStatusEnum.PENDING: 20,
            OrderStatusEnum.ACCEPTED: 10,
            OrderStatusEnum.PREPARING: 10,
            OrderStatusEnum.READY: 10,
            OrderStatusEnum.DELIVERING: 10,
            OrderStatusEnum.COMPLETED: 20,
            OrderStatusEnum.CANCELLED: 14,
            OrderStatusEnum.NOT_ACCEPTED: 6,
        }

        now = datetime.now(timezone.utc)
        created_pks = []

        self.stdout.write(f"Generating 100 orders for each of {len(target_cookers)} cookers...")

        with transaction.atomic():
            for cooker in target_cookers:
                dishes = dishes_by_cooker[cooker.id]
                drinks = drinks_by_cooker[cooker.id]
                for status, count in distribution.items():
                    for i in range(count):
                        customer = random.choice(customers)
                        address = random.choice(addresses)

                        # PENDING orders must stay within the expiry timeout window so
                        # expire_pending_orders doesn't immediately sweep them away:
                        #   ASAP timeout = IDLE_CANCEL_TIME_FOR_ASAP_DELIVERY (5 min)
                        #   Scheduled timeout = IDLE_CANCEL_TIME_FOR_SCHEDULED_DELIVERY (60 min)
                        if status == OrderStatusEnum.PENDING:
                            asap_limit = settings.IDLE_CANCEL_TIME_FOR_ASAP_DELIVERY - 1
                            created = now - timedelta(minutes=random.randint(1, asap_limit))
                        else:
                            created = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                        paid_date = created + timedelta(minutes=1)

                        accepted_date = None
                        preparing_date = None
                        ready_date = None
                        delivering_date = None
                        completed_date = None
                        cancelled_date = None
                        cancelled_by = None

                        if status in (
                            OrderStatusEnum.ACCEPTED,
                            OrderStatusEnum.PREPARING,
                            OrderStatusEnum.READY,
                            OrderStatusEnum.DELIVERING,
                            OrderStatusEnum.COMPLETED,
                        ):
                            accepted_date = paid_date + timedelta(minutes=random.randint(1, 10))

                        if status in (
                            OrderStatusEnum.PREPARING,
                            OrderStatusEnum.READY,
                            OrderStatusEnum.DELIVERING,
                            OrderStatusEnum.COMPLETED,
                        ):
                            assert accepted_date is not None
                            preparing_date = accepted_date + timedelta(minutes=random.randint(1, 5))

                        if status in (OrderStatusEnum.READY, OrderStatusEnum.DELIVERING, OrderStatusEnum.COMPLETED):
                            assert preparing_date is not None
                            ready_date = preparing_date + timedelta(minutes=random.randint(10, 30))

                        if status in (OrderStatusEnum.DELIVERING, OrderStatusEnum.COMPLETED):
                            assert ready_date is not None
                            delivering_date = ready_date + timedelta(minutes=random.randint(1, 5))

                        if status == OrderStatusEnum.COMPLETED:
                            assert delivering_date is not None
                            completed_date = delivering_date + timedelta(minutes=random.randint(10, 40))

                        if status == OrderStatusEnum.CANCELLED:
                            cancelled_date = paid_date + timedelta(minutes=random.randint(5, 60))
                            if i < 3:
                                cancelled_by = CancelledByEnum.COOKER
                            elif i < 6:
                                cancelled_by = CancelledByEnum.CUSTOMER
                            else:
                                cancelled_by = CancelledByEnum.SYSTEM

                        order = OrderModel.objects.create(
                            cooker=cooker,
                            customer=customer,
                            address=address,
                            status=status,
                            paid_date=paid_date,
                            accepted_date=accepted_date,
                            preparing_date=preparing_date,
                            ready_date=ready_date,
                            delivering_date=delivering_date,
                            completed_date=completed_date,
                            cancelled_date=cancelled_date,
                            cancelled_by=cancelled_by,
                            delivery_fees=round(random.uniform(2.0, 10.0), 2),
                            delivery_distance=round(random.uniform(500, 5000), 2),
                        )

                        # auto_now_add ignores the value passed to create() — update separately
                        OrderModel.objects.filter(pk=order.pk).update(created=created)

                        created_pks.append(order.pk)

                        if dishes and random.random() < 0.7:
                            for dish in random.sample(dishes, min(random.randint(1, 3), len(dishes))):
                                OrderDishItemModel.objects.create(
                                    order=order,
                                    dish=dish,
                                    dish_quantity=random.randint(1, 4),
                                )

                        if drinks and random.random() < 0.5:
                            for drink in random.sample(drinks, min(random.randint(1, 2), len(drinks))):
                                OrderDrinkItemModel.objects.create(
                                    order=order,
                                    drink=drink,
                                    drink_quantity=random.randint(1, 3),
                                )

        cooker_ids = [c.id for c in target_cookers]
        self.stdout.write(
            self.style.SUCCESS(
                f"Done — 100 orders per cooker {cooker_ids} (pks {min(created_pks)}–{max(created_pks)})."
            )
        )
