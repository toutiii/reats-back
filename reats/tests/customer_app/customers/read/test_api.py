from unittest.mock import ANY

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.fixture
def missing_customer_id() -> int:
    return 99999


@pytest.mark.django_db
def test_get_existing_customer_data(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{customer_id}/",
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "success": True,
        "data": {
            "id": 1,
            "firstname": "Ben",
            "lastname": "TEN",
            "phone": "+33700000001",
            "photo": ANY,
            "is_activated": True,
            "stripe_id": ANY,
            "is_deleted": False,
        },
        "message": "Operation successful",
    }


@pytest.mark.django_db
def test_get_missing_customer_data(
    auth_headers: dict,
    client: APIClient,
    missing_customer_id: int,
    path: str,
) -> None:
    response = client.get(
        f"{path}{missing_customer_id}/",
        follow=False,
        **auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json().get("success") is False
    assert response.json().get("data") is None
