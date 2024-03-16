import pytest
from customer_app.models import CustomerModel
from rest_framework import status
from rest_framework.test import APIClient


class TestReadAddressesSuccess:
    @pytest.fixture
    def customer_id(eslf) -> int:
        return 1

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_id: int,
        customer_address_path: str,
    ) -> None:

        # we check that the customer has some addresses
        assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 4

        # Then we list addresses
        response = client.get(
            customer_address_path,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "data": [
                {
                    "address_complement": "résidence test",
                    "customer": 1,
                    "id": 1,
                    "postal_code": "91100",
                    "street_name": "rue du terrier du rat",
                    "street_number": "1",
                    "town": "Villabé",
                },
                {
                    "address_complement": "résidence test",
                    "customer": 1,
                    "id": 2,
                    "postal_code": "91100",
                    "street_name": "rue du terrier du rat",
                    "street_number": "2",
                    "town": "Corbeil-Essonnes",
                },
                {
                    "address_complement": None,
                    "customer": 1,
                    "id": 3,
                    "postal_code": "91000",
                    "street_name": "rue du terrier du rat",
                    "street_number": "3",
                    "town": "Évry-Courcouronnes",
                },
                {
                    "address_complement": None,
                    "customer": 1,
                    "id": 4,
                    "postal_code": "91540",
                    "street_name": "rue du terrier du rat",
                    "street_number": "4",
                    "town": "Mennecy",
                },
            ],
            "ok": True,
            "status_code": 200,
        }
