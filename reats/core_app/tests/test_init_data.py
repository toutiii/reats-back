import pytest
from core_app.models import CookerModel, CustomerModel, DeliverModel, DishModel, DrinkModel, OrderModel
from django.contrib.auth import get_user_model
from django.core.management import call_command

User = get_user_model()


@pytest.mark.django_db
def test_init_data_command():
    """
    Test that the init_data command successfully creates users, menu items, and orders.
    """
    # Ensure database is clean (pytest-django handles this transactionally, but good to be sure logic works on empty db)
    assert CookerModel.objects.count() == 0
    assert CustomerModel.objects.count() == 0
    assert OrderModel.objects.count() == 0
    assert User.objects.count() == 0

    # Run the command
    call_command("init_data")

    # Verify Superuser
    assert User.objects.filter(username="admin@reats.com", is_superuser=True).exists()

    # Verify Users
    assert CookerModel.objects.filter(email="cooker@example.com").exists()
    assert CookerModel.objects.get(email="cooker@example.com").is_activated

    assert CustomerModel.objects.filter(phone="+33753790506").exists()
    assert CustomerModel.objects.get(phone="+33753790506").is_activated

    assert DeliverModel.objects.filter(phone="+33753790506").exists()
    deliver = DeliverModel.objects.get(phone="+33753790506")
    assert deliver.is_activated
    # assert deliver.is_online # Depending on logic, might toggle. init_data sets it to True.

    # Verify Menu
    cooker = CookerModel.objects.get(email="cooker@example.com")
    assert DishModel.objects.filter(cooker=cooker).count() >= 3
    assert DrinkModel.objects.filter(cooker=cooker).count() >= 2

    # Verify Orders
    order_count = OrderModel.objects.filter(cooker=cooker).count()
    assert order_count > 0
    # Check that we have different statuses
    statuses = set(OrderModel.objects.values_list("status", flat=True))
    assert len(statuses) > 1, "Should have multiple order statuses generated"

    initial_dish_count = DishModel.objects.count()
    call_command("init_data")

    assert DishModel.objects.count() == initial_dish_count, "Dishes should not be duplicated"
    assert CookerModel.objects.count() == 1, "Cooker should not be duplicated"
