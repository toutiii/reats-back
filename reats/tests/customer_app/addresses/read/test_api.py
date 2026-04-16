import pytest
from core_app.models import AddressModel
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum


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
        assert AddressModel.objects.filter(customer=customer_id).count() == 2

        # Then we list addresses
        response = client.get(
            customer_address_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "success": True,
            "message": SuccessMessageEnum.OPERATION_SUCCESSFUL,
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
