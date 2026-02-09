"""Tests for the Dashboard Popular Items endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum, TimeFrameEnum


@pytest.mark.django_db
class TestPopularItemsAPI:
    """Tests for the DashboardView popular_items action."""

    def test_get_popular_items_success(
        self,
        auth_headers: dict,
        client: APIClient,
        popular_items_path: str,
    ) -> None:
        """Test GET /dashboard/popular-items successfully."""
        response = client.get(
            popular_items_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "success" in response.json()
        assert "data" in response.json()
        assert "message" in response.json()
        assert response.json()["message"] == SuccessMessageEnum.OPERATION_SUCCESSFUL.value
        assert response.json()["success"] is True
        data = response.json()["data"]

        assert "results" in data
        assert "pagination" in data
        assert isinstance(data["results"], list)

    def test_get_popular_items_with_period(
        self,
        auth_headers: dict,
        client: APIClient,
        popular_items_path: str,
    ) -> None:
        """Test GET /dashboard/popular-items?period=month successfully."""
        response = client.get(
            popular_items_path,
            {"period": TimeFrameEnum.MONTH.value},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert "success" in response.json()
        assert "data" in response.json()

        assert response.json()["message"] == SuccessMessageEnum.OPERATION_SUCCESSFUL.value
        assert response.json()["success"] is True
        data = response.json()["data"]
        assert "results" in data

    def test_get_popular_items_pagination(
        self,
        auth_headers: dict,
        client: APIClient,
        popular_items_path: str,
    ) -> None:
        """Test pagination for popular items."""
        response = client.get(
            popular_items_path,
            {"page": 1, "page_size": 2},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert "success" in response.json()
        assert "data" in response.json()

        assert response.json()["message"] == SuccessMessageEnum.OPERATION_SUCCESSFUL.value
        assert response.json()["success"] is True

        data = response.json()["data"]
        assert "results" in data
        assert "pagination" in data
        assert len(data["results"]) <= 2
        assert data["pagination"]["items_per_page"] == 2

    def test_get_popular_items_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        popular_items_path: str,
    ) -> None:
        """Test the structure of popular items in the results."""
        response = client.get(
            popular_items_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.json()["data"]["results"]

        if len(results) > 0:
            item = results[0]
            assert "id" in item
            assert "name" in item
            assert "numberOfSoldItems" in item
            assert "revenue" in item
            assert "image" in item

    def test_get_popular_items_unauthenticated(
        self,
        client: APIClient,
        popular_items_path: str,
    ) -> None:
        """Test that unauthenticated access returns 401."""
        response = client.get(
            popular_items_path,
            follow=False,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
