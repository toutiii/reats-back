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
    client: APIClient,
    cooker_id: int,
    path: str,
) -> None:
    response = client.get(f"{path}{cooker_id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("data") == {
        "personal_infos_section": {
            "title": "personal_infos",
            "data": {
                "photo": "https://img-3.journaldesfemmes.fr/M_bbWpTVNekL5O_MLzQ4dyInmJU=/750x/smart/1c9fe4d4419047f18efc37134a046e5a/recipe-jdf/1001383.jpg",  # noqa
                "siret": "00000000000001",
                "firstname": "test",
                "lastname": "test",
                "phone": "0600000001",
                "max_order_number": "7",
            },
        },
        "address_section": {
            "title": "address",
            "data": {
                "street_number": "1",
                "street_name": "rue du terrier du rat",
                "address_complement": "résidence test",
                "postal_code": "91100",
                "town": "test",
            },
        },
    }


@pytest.mark.django_db
def test_get_missing_cooker_data(
    client: APIClient,
    missing_cooker_id: int,
    path: str,
) -> None:
    response = client.get(f"{path}{missing_cooker_id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("ok") is False
    assert response.json().get("data") is None
