import pytest
from core_app.models import AddressModel, CookerModel, CustomerModel, OrderModel
from django.urls import reverse


@pytest.fixture
def authenticated_user_id(auth_headers):
    return auth_headers.get("user_id", 1)


@pytest.fixture
def create_test_cooker(db):
    return CookerModel.objects.get(pk=1)


@pytest.fixture
def create_authenticated_customer(db, authenticated_user_id):
    return CustomerModel.objects.get(pk=1)


@pytest.fixture
def create_test_address(db, create_authenticated_customer):
    return AddressModel.objects.get(pk=1)


@pytest.fixture
def clean_authenticated_user_orders(create_authenticated_customer):
    customer = create_authenticated_customer
    OrderModel.objects.filter(customer=customer).delete()
    return customer


@pytest.fixture
def customer_order_path():
    return reverse("orders-list")
