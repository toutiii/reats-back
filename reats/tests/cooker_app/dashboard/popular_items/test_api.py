"""Tests for the Dashboard Popular Items endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import TimeFrameEnum


@pytest.mark.django_db
class TestPopularItemsAPI:
    """Tests for the DashboardView popular_items action."""

    def test_get_popular_items_success(self, get_popular_items):
        payload = get_popular_items()
        data = payload["data"]
        assert "results" in data
        assert "pagination" in data
        assert isinstance(data["results"], list)

    def test_get_popular_items_with_period(self, get_popular_items):
        """Test GET /dashboard/popular-items?period=month successfully."""
        payload = get_popular_items({"period": TimeFrameEnum.MONTH.value})
        data = payload["data"]
        assert "results" in data

    def test_get_popular_items_pagination(self, get_popular_items):
        """Test pagination for popular items."""
        payload = get_popular_items({"page": 1, "page_size": 2})
        data = payload["data"]
        assert "results" in data
        assert "pagination" in data
        assert len(data["results"]) <= 2
        assert data["pagination"]["items_per_page"] == 2

    def test_get_popular_items_structure(self, get_popular_items):
        """Test the structure of popular items in the results."""
        payload = get_popular_items()
        results = payload["data"]["results"]

        if results:
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
