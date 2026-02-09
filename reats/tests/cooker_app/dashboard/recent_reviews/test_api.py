"""Tests for the Dashboard Recent Reviews endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import SuccessMessageEnum


@pytest.mark.django_db
class TestRecentReviewsAPI:
    """Tests for the DashboardView recent_reviews action."""

    def test_get_recent_reviews_success(
        self,
        auth_headers: dict,
        client: APIClient,
        recent_reviews_path: str,
    ) -> None:
        """Test GET /dashboard/recent-reviews successfully."""
        response = client.get(
            recent_reviews_path,
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

    def test_get_recent_reviews_pagination(
        self,
        auth_headers: dict,
        client: APIClient,
        recent_reviews_path: str,
    ) -> None:
        """Test pagination for recent reviews."""
        response = client.get(
            recent_reviews_path,
            {"page": 1, "page_size": 2},
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
        assert isinstance(data["results"], list)
        assert isinstance(data["pagination"], dict)
        assert len(data["results"]) <= 2
        assert data["pagination"]["items_per_page"] == 2

    def test_get_recent_reviews_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        recent_reviews_path: str,
    ) -> None:
        """Test the structure of recent reviews in the results."""
        response = client.get(
            recent_reviews_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.json()["data"]["results"]

        if len(results) > 0:
            item = results[0]
            assert "id" in item
            assert "customerName" in item
            assert "rating" in item
            assert "comment" in item
            assert "date" in item
            assert "orderNumber" in item

    def test_get_recent_reviews_unauthenticated(
        self,
        client: APIClient,
        recent_reviews_path: str,
    ) -> None:
        """Test that unauthenticated access returns 401."""
        response = client.get(
            recent_reviews_path,
            follow=False,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
