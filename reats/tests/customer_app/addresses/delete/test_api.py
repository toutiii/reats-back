import pytest
from customer_app.models import AddressModel, CustomerModel
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 3


@pytest.fixture
def post_payload_1(customer_id: int) -> dict:
    return {
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test-1",
        "customer": customer_id,
    }


@pytest.fixture
def post_payload_2(customer_id: int) -> dict:
    return {
        "street_name": "rue du terrier du rat",
        "street_number": "2",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test-2",
        "customer": customer_id,
    }


@pytest.mark.django_db
def test_delete_address_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_address_path: str,
    post_payload_1: dict,
    post_payload_2: dict,
) -> None:

    # Fist create both addresses

    first_create_response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_payload_1),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert first_create_response.status_code == status.HTTP_201_CREATED
    assert first_create_response.json() == {"ok": True, "status_code": 201}

    first_address = AddressModel.objects.latest("pk")

    second_create_response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_payload_2),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert second_create_response.status_code == status.HTTP_201_CREATED
    assert second_create_response.json() == {"ok": True, "status_code": 201}

    second_address = AddressModel.objects.latest("pk")

    # Then we check that the customer has both addresses
    assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 2

    # Then we delete, for example, the 2nd address
    delete_response = client.delete(
        f"{customer_address_path}{second_address.pk}/",
        follow=False,
        **auth_headers,
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {"ok": True, "status_code": 200}

    # Then we check that the 2nd address is not in the database anymore
    second_address_dict = model_to_dict(AddressModel.objects.get(pk=second_address.pk))
    del second_address_dict["id"]
    assert second_address_dict == {
        "street_name": "rue du terrier du rat",
        "street_number": "2",
        "postal_code": "91100",
        "address_complement": "résidence test",
        "town": "Ville-De-Test-2",
        "is_enabled": False,
        "customer": customer_id,
    }

    # Then we check that the 1st address is still in the database
    assert AddressModel.objects.filter(pk=first_address.pk).exists()

    # Then we check that the customer still has both addresses
    assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 2


@pytest.mark.django_db
def test_delete_address_failed_not_existing(
    auth_headers: dict,
    client: APIClient,
    customer_address_path: str,
) -> None:

    # Then we try to delete an address that does not exist
    delete_response = client.delete(
        f"{customer_address_path}999/",
        follow=False,
        **auth_headers,
    )
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND
    assert delete_response.json() == {"ok": False, "status_code": 404}


@pytest.mark.django_db
def test_delete_customer_will_also_delete_his_addresses(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    path: str,
    customer_address_path: str,
    post_payload_1: dict,
    post_payload_2: dict,
) -> None:

    # Fist create both addresses

    first_create_response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_payload_1),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert first_create_response.status_code == status.HTTP_201_CREATED
    assert first_create_response.json() == {"ok": True, "status_code": 201}

    first_address = AddressModel.objects.latest("pk")

    second_create_response = client.post(
        customer_address_path,
        encode_multipart(BOUNDARY, post_payload_2),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **auth_headers,
    )
    assert second_create_response.status_code == status.HTTP_201_CREATED
    assert second_create_response.json() == {"ok": True, "status_code": 201}

    second_address = AddressModel.objects.latest("pk")

    # Then we check that the customer has both addresses
    assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 2

    # Then we delete the customer
    delete_response = client.delete(
        f"{path}{customer_id}/",
        follow=False,
        **auth_headers,
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {"ok": True, "status_code": 200}

    # Then we check that the 1st address is not in the database anymore
    assert not AddressModel.objects.filter(pk=first_address.pk).exists()

    # Then we check that the 2nd address is not in the database anymore
    assert not AddressModel.objects.filter(pk=second_address.pk).exists()

    # Then we check that the customer is not in the database anymore
    assert not CustomerModel.objects.filter(pk=customer_id).exists()


@pytest.mark.django_db
class TestDeleteAddressFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000001"}

    def test_response(
        self,
        customer_api_key_header: dict,
        client: APIClient,
        data: dict,
        customer_address_path: str,
    ) -> None:
        address_id = 1

        with freeze_time("2024-01-20T17:05:45+00:00"):
            token_response = client.post(
                "/api/v1/token/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **customer_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:30:45+00:00"):
            response = client.delete(
                f"{customer_address_path}{address_id}/",
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error_code") == "token_not_valid"
