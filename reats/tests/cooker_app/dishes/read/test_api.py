import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient


def test_empty_query_params(client: APIClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("data") is None
    assert response.json() == {"ok": True, "status_code": status.HTTP_404_NOT_FOUND}


@pytest.mark.django_db
def test_get_enabled_dishes(client: APIClient, path: str) -> None:
    response = client.get(path, {"is_enabled": "true"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_disabled_dishes(client: APIClient, path: str) -> None:
    response = client.get(path, {"is_enabled": "false"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is False


@pytest.mark.django_db
def test_get_starters(client: APIClient, path: str) -> None:
    response = client.get(path, {"category": "starter"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "starter"


@pytest.mark.django_db
def test_get_dishes(client: APIClient, path: str) -> None:
    response = client.get(path, {"category": "dish"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dish"


@pytest.mark.django_db
def test_get_desserts(client: APIClient, path: str) -> None:
    response = client.get(path, {"category": "dessert"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dessert"


@pytest.mark.django_db
def test_get_all_categories(client: APIClient, path: str) -> None:
    response = client.get(path, {"category": "starter,dish,dessert"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") in (True, False)


@pytest.mark.django_db
def test_get_all_enabled_categories(client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "true",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_all_disabled_categories(client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "false",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is False
