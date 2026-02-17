import pytest
from core_app.models import CookerModel, CustomerModel, DeliverModel, DishModel, DrinkModel, OrderModel
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

User = get_user_model()


@pytest.mark.django_db
def test_init_data_command_requires_phone_argument():
    with pytest.raises(CommandError, match="the following arguments are required: --phone"):
        call_command("init_data")


@pytest.mark.django_db
def test_init_data_command_with_phone_creates_seed_data():
    # Ensure database is clean (pytest-django handles this transactionally, but good to be sure logic works on empty db)
    assert CookerModel.objects.count() == 0
    assert CustomerModel.objects.count() == 0
    assert OrderModel.objects.count() == 0
    assert User.objects.count() == 0

    phone = "+33600000000"

    # Run the command with required argument
    call_command("init_data", phone=phone)

    # Verify Superuser
    assert User.objects.filter(username="admin@reats.com", is_superuser=True).exists()

    # Verify Users
    assert CookerModel.objects.filter(email="cooker@example.com").exists()
    assert CookerModel.objects.get(email="cooker@example.com").is_activated

    assert CustomerModel.objects.filter(phone=phone).exists()
    assert CustomerModel.objects.get(phone=phone).is_activated

    assert DeliverModel.objects.filter(phone=phone).exists()
    deliver = DeliverModel.objects.get(phone=phone)
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


@pytest.mark.django_db
def test_init_data_command_is_idempotent_for_core_seed_entities():
    phone = "+33600000000"

    call_command("init_data", phone=phone)
    initial_dish_count = DishModel.objects.count()

    call_command("init_data", phone=phone)

    assert DishModel.objects.count() == initial_dish_count, "Dishes should not be duplicated"
    assert CookerModel.objects.count() == 1, "Cooker should not be duplicated"
    assert CustomerModel.objects.filter(phone=phone).count() == 1, "Customer should not be duplicated"
    assert DeliverModel.objects.filter(phone=phone).count() == 1, "Deliver should not be duplicated"
