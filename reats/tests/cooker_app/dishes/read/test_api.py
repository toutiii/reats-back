import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_empty_query_params(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("data") is None
    assert response.json() == {"ok": True, "status_code": status.HTTP_404_NOT_FOUND}


@pytest.mark.django_db
def test_get_enabled_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"is_enabled": "true"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_disabled_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"is_enabled": "false"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is False


@pytest.mark.django_db
def test_get_starters(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "starter"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "starter"


@pytest.mark.django_db
def test_get_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "dish"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dish"


@pytest.mark.django_db
def test_get_desserts(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "dessert"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dessert"


@pytest.mark.django_db
def test_get_all_categories(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "starter,dish,dessert"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") in (True, False)


@pytest.mark.django_db
def test_get_all_enabled_categories(
    auth_headers: dict, client: APIClient, path: str
) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "true",
        },
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_all_disabled_categories(
    auth_headers: dict, client: APIClient, path: str
) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "false",
        },
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is False
