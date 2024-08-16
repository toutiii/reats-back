import pytest
from rest_framework import status
from rest_framework.test import APIClient


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
    assert response.json().get("ok") is True
    assert response.json() == {
        "data": {
            "address_section": {
                "data": {
                    "address_complement": None,
                    "postal_code": "91000",
                    "street_name": "rue André Lalande",
                    "street_number": "1",
                    "town": "Evry",
                },
                "title": "address",
            },
            "personal_infos_section": {
                "data": {
                    "firstname": "test",
                    "is_online": True,
                    "lastname": "test",
                    "max_order_number": "10",
                    "phone": "0600000001",
                    "photo": "https://some-url.com",
                    "siret": "00000000000001",
                },
                "title": "personal_infos",
            },
        },
        "ok": True,
        "status_code": 200,
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
    assert response.json().get("ok") is False
    assert response.json().get("data") is None
