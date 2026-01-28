"""Tests pour l'endpoint Dashboard Stats."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestDashboardStatsAPI:
    """Tests de l'action stats du DashboardView."""

    def test_get_stats_today_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=today avec succès."""
        response = client.get(
            dashboard_stats_path,
            {"period": "today"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert getattr(response.json(), "data")
        data = response.json()["data"]

        assert isinstance(data, dict)
        assert getattr(data, "period")
        assert data["period"] == "today"
        assert "stats" in data
        assert "revenueChart" in data
        assert "recentReviews" in data
        assert "popularItems" in data

        # Vérification des stats clés
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
        """Test GET /dashboard/stats?period=week avec succès."""
        response = client.get(
            dashboard_stats_path,
            {"period": "week"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["period"] == "week"
        assert len(data["revenueChart"]["labels"]) == 7  # 7 jours

    def test_get_stats_month_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=month avec succès."""
        response = client.get(
            dashboard_stats_path,
            {"period": "month"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["period"] == "month"
        assert len(data["revenueChart"]["labels"]) == 4  # 4 semaines

    def test_get_stats_year_success(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test GET /dashboard/stats?period=year avec succès."""
        response = client.get(
            dashboard_stats_path,
            {"period": "year"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["period"] == "year"
        assert len(data["revenueChart"]["labels"]) == 12  # 12 mois

    def test_get_stats_default_period_is_today(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test que la période par défaut est 'today'."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["period"] == "today"

    def test_revenue_chart_structure(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test la structure du graphique de revenus."""
        response = client.get(
            dashboard_stats_path,
            {"period": "today"},
            follow=False,
            **auth_headers,
        )

        chart = response.json()["data"]["revenueChart"]
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
        """Test la structure des avis récents."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        reviews = response.json()["data"]["recentReviews"]
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
        """Test la structure des articles populaires."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        items = response.json()["data"]["popularItems"]
        assert isinstance(items, list)

        if len(items) > 0:
            item = items[0]
            assert "id" in item
            assert "name" in item
            assert "soldToday" in item
            assert "revenue" in item
            assert "image" in item

    def test_stats_contains_active_orders_count(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test que les stats contiennent le compte des commandes actives."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        stats = response.json()["data"]["stats"]

        # Commandes actives = PENDING + PROCESSING + COMPLETED
        assert stats["activeOrders"]["count"] >= 2  # Au moins PENDING et PROCESSING
        assert stats["pendingOrders"]["count"] >= 1  # Au moins 1 PENDING

    def test_stats_contains_revenue_with_currency(
        self,
        auth_headers: dict,
        client: APIClient,
        dashboard_stats_path: str,
    ) -> None:
        """Test que les revenus ont une devise."""
        response = client.get(
            dashboard_stats_path,
            follow=False,
            **auth_headers,
        )

        revenue = response.json()["data"]["stats"]["revenue"]
        assert "amount" in revenue
        assert "currency" in revenue
        assert revenue["currency"] == "EUR"
