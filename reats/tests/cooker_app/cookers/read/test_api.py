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
    assert response.json().get("data") is not None  # TODO: A json schema here


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
