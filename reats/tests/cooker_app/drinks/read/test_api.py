import pytest
from rest_framework import status
from rest_framework.test import APIClient


def test_empty_query_params(client: APIClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("data") is None
    assert response.json() == {"ok": True, "status_code": status.HTTP_404_NOT_FOUND}


@pytest.mark.django_db
def test_get_enabled_drinks(client: APIClient, path: str) -> None:
    response = client.get(path, {"is_enabled": "true"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_disabled_drinks(client: APIClient, path: str) -> None:
    response = client.get(path, {"is_enabled": "false"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is False
