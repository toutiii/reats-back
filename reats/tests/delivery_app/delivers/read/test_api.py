import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def deliver_id() -> int:
    return 1


@pytest.fixture
def missing_deliver_id() -> int:
    return 99999


@pytest.mark.django_db
def test_get_existing_deliver_data(
    auth_headers: dict,
    client: APIClient,
    deliver_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{deliver_id}/",
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": {
            "personal_infos_section": {
                "data": {
                    "delivery_radius": 15,
                    "town": "Evry-Courcouronnes",
                    "delivery_vehicle": "bike",
                    "firstname": "John test delivery " "man",
                    "lastname": "DOE",
                    "phone": "0700000001",
                    "photo": "https://some-url.com",
                    "siret": "00000000000000",
                },
                "title": "personal_infos",
            }
        },
        "ok": True,
        "status_code": 200,
    }


@pytest.mark.django_db
def test_get_missing_deliver_data(
    auth_headers: dict,
    client: APIClient,
    missing_deliver_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{missing_deliver_id}/",
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("ok") is False
    assert response.json().get("data") is None
