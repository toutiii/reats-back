import pytest
from core_app.models import AddressModel, CookerModel, CustomerModel, OrderModel
from django.urls import reverse


@pytest.fixture
def authenticated_user_id(auth_headers):
    return auth_headers.get("user_id", 1)


@pytest.fixture
def create_test_cooker():
    cooker, created = CookerModel.objects.get_or_create(
        firstname="Test",
        lastname="Cooker",
        phone="0600000001",
        email="test_fixture@gmail.com",
        postal_code="75001",
        siret="12345678901234",
        street_name="Rue de test",
        street_number="1",
        town="Paris",
        max_order_number=10,
        is_activated=True,
        defaults={"acceptance_rate": 100.0, "photo": "cookers/1/profile_pics/default-profile-pic.jpg"},
    )
    return cooker


@pytest.fixture
def create_authenticated_customer(authenticated_user_id):
    try:
        return CustomerModel.objects.get(id=authenticated_user_id)
    except CustomerModel.DoesNotExist:
        return CustomerModel.objects.create(
            id=authenticated_user_id,
            firstname="Test",
            lastname="Customer",
            phone=f"0600000{authenticated_user_id:03d}",
            is_activated=True,
            photo="customers/1/profile_pics/default-profile-pic.jpg",
        )


@pytest.fixture
def create_test_address(create_authenticated_customer):
    customer = create_authenticated_customer
    address, created = AddressModel.objects.get_or_create(
        street_name="Rue de test",
        street_number="1",
        town="Paris",
        postal_code="75001",
        customer=customer,
        defaults={"is_enabled": True},
    )
    return address


@pytest.fixture
def clean_authenticated_user_orders(create_authenticated_customer):
    customer = create_authenticated_customer
    OrderModel.objects.filter(customer=customer).delete()
    return customer


@pytest.fixture
def customer_order_path():
    return reverse("orders-list")
