import pytest
from core_app.models import DishModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestDishAvailabilityToggle:
    """Tests for PATCH /api/v1/dishes/:id/availability/"""

    def test_toggle_from_enabled_to_disabled(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        # Dish pk=4 belongs to cooker 1 and is enabled by default
        dish = DishModel.objects.get(pk=4)
        assert dish.is_enabled is True

        response = client.patch(
            f"{path}{dish.pk}/availability/",
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        dish.refresh_from_db()
        assert dish.is_enabled is False
        assert response.json()["data"]["is_enabled"] is False

    def test_toggle_from_disabled_to_enabled(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        # Dish pk=10 belongs to cooker 1 and is disabled (is_enabled=false in fixture)
        dish = DishModel.objects.get(pk=10)
        assert dish.is_enabled is False

        response = client.patch(
            f"{path}{dish.pk}/availability/",
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success") is True
        dish.refresh_from_db()
        assert dish.is_enabled is True
        assert response.json()["data"]["is_enabled"] is True

    def test_toggle_returns_404_for_other_cooker_dish(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        # Dish pk=1 belongs to cooker 4, not cooker 1 (auth_headers is for cooker 1)
        response = client.patch(
            f"{path}1/availability/",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestDishSearchFilter:
    """Tests for GET /api/v1/dishes/?search=<name>"""

    def test_search_returns_matching_dishes(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        response = client.get(
            path,
            {"search": "poulet", "is_enabled": "true"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data")
        assert len(data) > 0
        for item in data:
            assert "poulet" in item["name"].lower()

    def test_search_is_case_insensitive(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        response = client.get(
            path,
            {"search": "POULET", "is_enabled": "true"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data")
        assert len(data) > 0

    def test_search_returns_empty_for_no_match(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        response = client.get(
            path,
            {"search": "xyznotexist", "is_enabled": "true"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("data") == []


@pytest.mark.django_db
class TestDishAvailableFilter:
    """Tests for GET /api/v1/dishes/?available=true|false"""

    def test_available_true_returns_only_enabled(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        response = client.get(
            path,
            {"available": "true"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data")
        assert len(data) > 0
        for item in data:
            assert item["is_enabled"] is True

    def test_available_false_returns_only_disabled(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        response = client.get(
            path,
            {"available": "false", "is_enabled": "false"},
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data")
        assert len(data) > 0
        for item in data:
            assert item["is_enabled"] is False
