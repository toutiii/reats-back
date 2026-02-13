import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum


@pytest.fixture
def get_recent_reviews(client: APIClient, auth_headers: dict, recent_reviews_path: str):
    """Fixture to call recent reviews endpoint and assert basic success."""

    def _call(params: dict | None = None) -> dict:
        response = client.get(
            recent_reviews_path,
            params or None,
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        payload = response.json()
        assert payload["message"] == SuccessMessageEnum.OPERATION_SUCCESSFUL.value
        assert payload["success"] is True
        assert "data" in payload
        return payload

    return _call
