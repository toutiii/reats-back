import pytest
from customer_app.models import CustomerModel
from rest_framework import status
from rest_framework.test import APIClient


class TestReadAddressesSuccess:
    @pytest.fixture
    def customer_id(self) -> int:
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
        assert CustomerModel.objects.get(pk=customer_id).addresses.count() == 2

        # Then we list addresses
        response = client.get(
            customer_address_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": 200,
            "data": [
                {
                    "id": 1,
                    "street_name": "rue rené cassin",
                    "street_number": "1",
                    "town": "Corbeil-Essonnes",
                    "postal_code": "91100",
                    "address_complement": "résidence neptune",
                    "customer": 1,
                },
                {
                    "id": 2,
                    "street_name": "rue des Mazières",
                    "street_number": "13",
                    "town": "Evry",
                    "postal_code": "91000",
                    "address_complement": None,
                    "customer": 1,
                },
            ],
        }
