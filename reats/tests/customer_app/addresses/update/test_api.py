import pytest
from customer_app.models import AddressModel
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 3


@pytest.fixture
def post_payload(customer_id: int) -> dict:
    return {
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test",
        "customer": customer_id,
    }


@pytest.fixture
def update_payload(customer_id: int) -> dict:
    return {
        "street_name": "rue du nouveau terrier du rat",
        "street_number": "99",
        "postal_code": "91100",
        "address_complement": "résidence nouveau test",
        "town": "Ville-De-Nouveau-Test",
        "customer": customer_id,
    }


@pytest.mark.django_db
def test_update_address_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_address_path: str,
    post_payload: dict,
    update_payload: dict,
) -> None:

    # Fist create an address

    response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_payload),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"ok": True, "status_code": 201}

    # Then update the address
    update_response = client.put(
        f"{customer_address_path}{AddressModel.objects.latest('pk').pk}/",
        encode_multipart(BOUNDARY, update_payload),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json() == {"ok": True, "status_code": 200}

    new_address = model_to_dict(AddressModel.objects.latest("pk"))
    del new_address["id"]
    assert new_address == {
        "street_name": "rue du nouveau terrier du rat",
        "street_number": "99",
        "postal_code": "91100",
        "address_complement": "résidence nouveau test",
        "town": "Ville-De-Nouveau-Test",
        "customer": customer_id,
        "is_enabled": True,
    }
