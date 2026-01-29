import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum, ErrorMessageEnum, SuccessMessageEnum


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.fixture
def missing_cooker_id() -> int:
    return 0


@pytest.mark.django_db
def test_get_existing_cooker_data(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{cooker_id}/",
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("success") is True
    assert response.json() == {
        "success": True,
        "message": SuccessMessageEnum.OPERATION_SUCCESSFUL.value,
        "data": {
            "address_section": {
                "address_complement": None,
                "postal_code": "91000",
                "street_name": "rue André Lalande",
                "street_number": "1",
                "town": "Evry",
            },
            "personal_infos_section": {
                "acceptance_rate": 100.0,
                "firstname": "test",
                "is_online": True,
                "lastname": "test",
                "max_order_number": "10",
                "phone": "0766964170",
                "photo": "https://some-url.com",
                "siret": "00000000000001",
                "email": "test@gmail.com",
            },
        },
    }


@pytest.mark.django_db
def test_get_missing_cooker_data(
    auth_headers: dict,
    client: APIClient,
    missing_cooker_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{missing_cooker_id}/",
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("success") is False
    assert response.json().get("error").get("code") == ErrorCodeEnum.NOT_FOUND
    assert response.json().get("error").get("message") == ErrorMessageEnum.NOT_FOUND
