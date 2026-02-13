"""Tests for the Dashboard Recent Reviews endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestRecentReviewsAPI:
    """Tests for the DashboardView recent_reviews action."""

    def test_get_recent_reviews_success(self, get_recent_reviews) -> None:
        """Test GET /dashboard/recent-reviews successfully."""
        payload = get_recent_reviews()
        data = payload["data"]

        assert "results" in data
        assert "pagination" in data
        assert isinstance(data["results"], list)

    def test_get_recent_reviews_pagination(self, get_recent_reviews) -> None:
        """Test pagination for recent reviews."""
        payload = get_recent_reviews({"page": 1, "page_size": 2})
        data = payload["data"]

        assert isinstance(data["results"], list)
        assert isinstance(data["pagination"], dict)
        assert len(data["results"]) <= 2
        assert data["pagination"]["items_per_page"] == 2

    def test_get_recent_reviews_structure(self, get_recent_reviews) -> None:
        """Test the structure of recent reviews in the results."""
        payload = get_recent_reviews()
        results = payload["data"]["results"]

        if len(results) > 0:
            item = results[0]
            assert "id" in item
            assert "customerName" in item
            # Verify "FirstName L." format (First name + space + 1 letter + dot)
            name_parts = item["customerName"].split(" ")
            assert len(name_parts) >= 2
            assert name_parts[-1].endswith(".")
            assert len(name_parts[-1]) == 2
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
