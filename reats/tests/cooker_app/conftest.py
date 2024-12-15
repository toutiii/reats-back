import random
from datetime import datetime, timedelta, timezone

import pytest
from cooker_app.models import CookerModel
from customer_app.models import AddressModel, CustomerModel, OrderModel
from django.db import transaction


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"


@pytest.fixture(scope="session")
def dashboard_path() -> str:
    return "/api/v1/cookers-dashboard/"


@pytest.fixture
def create_orders(custom_counts: dict):
    """
    Creates a specific number of orders for each status based on
    the custom_counts dictionary.

    Args:
        custom_counts (dict): A dictionary where keys are statuses (str)
        and values are the number of orders (int).
    """

    cooker_id = 1
    customer_id = 1
    address_id = 2

    # Use a transaction for bulk creation
    with transaction.atomic():
        for state, count in custom_counts.items():
            for _ in range(count):
                # Create a new order
                order = OrderModel.objects.create(
                    cooker=CookerModel.objects.get(id=cooker_id),
                    customer=CustomerModel.objects.get(id=customer_id),
                    address=AddressModel.objects.get(id=address_id),
                    status=state,
                    scheduled_delivery_date=datetime.now(timezone.utc)
                    + timedelta(days=random.randint(1, 10)),
                    delivery_fees=random.uniform(5.0, 20.0),
                    delivery_distance=random.uniform(1.0, 10.0),
                )

                print(f"Created order {order.id} in state '{state}'")
