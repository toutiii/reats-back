"""Tests for the Dashboard Stats endpoint."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import TimeFrameEnum


@pytest.mark.django_db
class TestDashboardStatsAPI:
    """Tests for the DashboardView stats action."""

    def test_get_stats_today_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=today successfully."""
        response = client.get(
            dashboard_stats_path,
            {"period": TimeFrameEnum.TODAY.value},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "period" in data
        assert data["period"] == TimeFrameEnum.TODAY.value
        assert "stats" in data
        assert "revenueChart" in data
        assert "recentReviews" in data
        assert "popularItems" in data

        # Verify key stats
        stats = data["stats"]
        assert "activeOrders" in stats
        assert "pendingOrders" in stats
        assert "revenue" in stats
        assert "customersServed" in stats

    def test_get_stats_week_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=week successfully."""
        response = client.get(
            dashboard_stats_path,
            {"period": TimeFrameEnum.WEEK.value},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "period" in data
        assert data["period"] == TimeFrameEnum.WEEK.value
        assert len(data["revenueChart"]["labels"]) == 7  # 7 days

    def test_get_stats_month_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=month successfully."""
        response = client.get(
            dashboard_stats_path,
            {"period": TimeFrameEnum.MONTH.value},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "period" in data
        assert data["period"] == TimeFrameEnum.MONTH.value
        assert len(data["revenueChart"]["labels"]) == 4  # 4 weeks

    def test_get_stats_year_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=year successfully."""
        response = client.get(
            dashboard_stats_path,
            {"period": TimeFrameEnum.YEAR.value},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "period" in data
        assert data["period"] == TimeFrameEnum.YEAR.value
        assert len(data["revenueChart"]["labels"]) == 12  # 12 months

    def test_get_stats_default_period_is_today(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that the default period is 'today'."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "period" in data
        assert data["period"] == TimeFrameEnum.TODAY.value

    def test_revenue_chart_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test the revenue chart structure."""
        response = client.get(
            dashboard_stats_path,
            {"period": "today"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "revenueChart" in data
        chart = data["revenueChart"]

        assert "labels" in chart
        assert "data" in chart
        assert len(chart["labels"]) == 6  # 6 intervalles de 4h
        assert len(chart["data"]) == 6

    def test_recent_reviews_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test the recent reviews structure."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "recentReviews" in data
        reviews = data["recentReviews"]
        assert isinstance(reviews, list)

        if len(reviews) > 0:
            review = reviews[0]
            assert "id" in review
            assert "customerName" in review
            assert "rating" in review
            assert "comment" in review
            assert "date" in review
            assert "orderNumber" in review

    def test_popular_items_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test the popular items structure."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "popularItems" in data
        items = data["popularItems"]
        assert isinstance(items, list)

        if len(items) > 0:
            item = items[0]
            assert "id" in item
            assert "name" in item
            assert "numberOfSoldItems" in item
            assert "revenue" in item
            assert "image" in item

    def test_stats_contains_active_orders_count(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that stats contain the active orders count."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "stats" in data
        stats = data["stats"]

        # Active orders = PENDING + PROCESSING + COMPLETED
        assert stats["activeOrders"]["count"] >= 2  # At least PENDING and PROCESSING
        assert stats["pendingOrders"]["count"] >= 1  # At least 1 PENDING

    def test_stats_contains_revenue_with_currency(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that revenue has a currency."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert "stats" in data
        stats = data["stats"]

        revenue = stats["revenue"]
        assert "amount" in revenue
        assert "currency" in revenue
        assert revenue["currency"] == "EUR"

    def test_stats_unauthenticated_returns_401(
        self,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that unauthenticated access returns 401."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_stats_invalid_period_defaults_to_today(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that an invalid period defaults to 'today' logic."""
        response = client.get(
            dashboard_stats_path,
            {"period": "invalid_period"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "data" in response.json()
        data = response.json()["data"]

        # An invalid period should be treated as 'today'
        assert data["period"] == "invalid_period"  # The returned period is the one passed
        # But the data is calculated with 'today' logic (6 intervals)
        assert len(data["revenueChart"]["labels"]) == 6

    def test_stats_empty_reviews_returns_empty_list(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that recentReviews returns an empty list if no reviews."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # recentReviews should be a list (can be empty)
        assert isinstance(data["recentReviews"], list)

    def test_stats_popular_items_handles_missing_photos(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test that popular items handle missing photos."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # popularItems should be a list
        assert isinstance(data["popularItems"], list)
        # Each item should have an 'image' key (can be None)
        for item in data["popularItems"]:
            assert "image" in item
