import pytest
from customer_app.models import AddressModel, CustomerModel
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 3


@pytest.fixture
def post_data(customer_id: int) -> dict:
    return {
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test",
        "customer": customer_id,
    }


@pytest.mark.django_db
def test_create_address_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_address_path: str,
    post_data: dict,
) -> None:
    old_count = AddressModel.objects.count()

    response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    new_count = AddressModel.objects.count()

    assert new_count - old_count == 1
    address = model_to_dict(AddressModel.objects.latest("pk"))
    del address["id"]
    assert address == {
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test",
        "customer": customer_id,
    }
    assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 1
    assert CustomerModel.objects.get(
        pk=customer_id
    ).addresses.first() == AddressModel.objects.latest("pk")

    assert response.json() == {"ok": True, "status_code": 201}
