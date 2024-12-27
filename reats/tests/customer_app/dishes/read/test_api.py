from unittest.mock import MagicMock

import pytest
from deepdiff import DeepDiff
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.parametrize(
    "query_parameter",
    [
        {
            "search_address_id": "1",
        },
        {
            "name": "pou",
            "search_address_id": "1",
        },
        {
            "country": "Cameroun",
            "search_address_id": "1",
        },
        {
            "search_radius": "2",
            "search_address_id": "1",
        },
        {
            "name": "pou",
            "country": "Cameroun",
            "search_address_id": "1",
        },
    ],
    ids=[
        "search_by_address",
        "search_by_name and address",
        "search_by_country and address",
        "search_by_radius and address",
        "search_by_name_and_country and_address",
    ],
)
class TestListDishesForCustomerNoResultsWithQueryParameterGivenByUser:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
        query_parameter: dict,
        mock_googlemaps_distance_matrix: MagicMock,
    ) -> None:

        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
            data=query_parameter,
        )
        assert response.status_code == status.HTTP_200_OK
        mock_googlemaps_distance_matrix.assert_called_once()
        if query_parameter.get("search_radius") == "2":
            assert response.json().get("ok") is True
            assert response.json().get("status_code") == status.HTTP_404_NOT_FOUND
            assert not response.json().get("data")


@pytest.mark.parametrize(
    "query_parameter",
    [
        {
            "search_radius": "10",
            "search_address_id": "1",
        },
        {
            "name": "pou",
            "country": "Cameroun",
            "search_address_id": "1",
            "search_radius": "10",
        },
    ],
    ids=[
        "search_by_radius",
        "search_by_name_and_country_and_radius_and_address",
    ],
)
class TestListDishesForCustomerSuccessWithQueryParameterGivenByUser:
    @pytest.fixture
    def expected_data_when_name_in_query_parameter(self) -> list[dict]:
        return [
            {
                "id": "5",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet braisé",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": True,
            },
            {
                "id": "6",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet DG",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
        ]

    @pytest.fixture
    def expected_data(self) -> list[dict]:
        return [
            {
                "category": "dish",
                "cooker": "4",
                "country": "Congo",
                "description": "Test",
                "id": "2",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "name": "Gombo porc riz",
                "photo": "https://some-url.com",
                "price": "13.0",
            },
            {
                "category": "dish",
                "cooker": "4",
                "country": "Cameroun",
                "description": "Test",
                "id": "3",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": True,
                "is_suitable_for_scheduled_delivery": False,
                "name": "Eru fufu",
                "photo": "https://some-url.com",
                "price": "15.0",
            },
            {
                "id": "4",
                "category": "dish",
                "country": "Benin",
                "description": "Test",
                "name": "Okok manioc",
                "price": "15.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "5",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet braisé",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": True,
            },
            {
                "id": "6",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet DG",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "7",
                "category": "dish",
                "country": "Nigeria",
                "description": "Test",
                "name": "Koki patate douce",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
            {
                "id": "8",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Ndolé Riz",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "cooker": "1",
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
            },
        ]

    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
        query_parameter: dict,
        mock_googlemaps_distance_matrix: MagicMock,
        expected_data: list[dict],
        expected_data_when_name_in_query_parameter: list[dict],
    ) -> None:

        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
            data=query_parameter,
        )
        assert response.status_code == status.HTTP_200_OK
        mock_googlemaps_distance_matrix.assert_called_once()

        assert response.json().get("ok") is True
        assert response.json().get("status_code") == 200

        if "name" in query_parameter and "country" in query_parameter:
            diff = DeepDiff(
                response.json().get("data"),
                expected_data_when_name_in_query_parameter,
                ignore_order=True,
            )
        else:
            diff = DeepDiff(
                response.json().get("data"),
                expected_data,
                ignore_order=True,
            )

        assert not diff


class TestListDishesForCustomerWithMissingSearchAddressId:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
    ) -> None:

        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "ok": False,
            "status_code": status.HTTP_400_BAD_REQUEST,
        }


@pytest.mark.parametrize(
    "query_parameter,expected_results",
    [
        (
            {
                "delivery_mode": "now",
                "search_address_id": "1",
            },
            {
                "ok": True,
                "status_code": 200,
                "data": [
                    {
                        "id": "3",
                        "category": "dish",
                        "country": "Cameroun",
                        "description": "Test",
                        "name": "Eru fufu",
                        "price": "15.0",
                        "photo": "https://some-url.com",
                        "cooker": "4",
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": True,
                        "is_suitable_for_scheduled_delivery": False,
                    }
                ],
            },
        ),
        (
            {
                "delivery_mode": "scheduled",
                "search_address_id": "1",
            },
            {
                "ok": True,
                "status_code": 200,
                "data": [
                    {
                        "id": "5",
                        "category": "dish",
                        "country": "Cameroun",
                        "description": "Test",
                        "name": "Poulet braisé",
                        "price": "11.0",
                        "photo": "https://some-url.com",
                        "cooker": "1",
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": True,
                    }
                ],
            },
        ),
    ],
    ids=[
        "search_by_delivery_mode_now",
        "search_by_delivery_mode_scheduled",
    ],
)
class TestListDishesWithDeliveryModeFilter:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
        query_parameter: dict,
        mock_googlemaps_distance_matrix: MagicMock,
        expected_results: dict,
    ):
        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
            data=query_parameter,
        )

        assert response.status_code == status.HTTP_200_OK
        mock_googlemaps_distance_matrix.assert_called_once()

        assert response.json() == expected_results


@pytest.mark.parametrize(
    "query_parameter,expected_results",
    [
        (
            {
                "cooker_id": "1",
                "search_address_id": "1",
                "delivery_mode": "scheduled",
            },
            {
                "data": [
                    {
                        "category": "dish",
                        "cooker": "1",
                        "country": "Cameroun",
                        "description": "Test",
                        "id": "5",
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": True,
                        "name": "Poulet braisé",
                        "photo": "https://some-url.com",
                        "price": "11.0",
                    }
                ],
                "ok": True,
                "status_code": 200,
            },
        ),
    ],
    ids=[
        "search_by_cooker_id",
    ],
)
class TestListDishesWithCookerIdFilter:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
        query_parameter: dict,
        mock_googlemaps_distance_matrix: MagicMock,
        expected_results: dict,
    ):
        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
            data=query_parameter,
        )

        assert response.status_code == status.HTTP_200_OK
        mock_googlemaps_distance_matrix.assert_called_once()
        assert response.json() == expected_results
