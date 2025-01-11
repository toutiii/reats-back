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
            assert response.json().get("status_code") == status.HTTP_200_OK
            assert response.json().get("data") == []


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
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet braisé",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": True,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "6",
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet DG",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
        ]

    @pytest.fixture
    def expected_data(self) -> list[dict]:
        return [
            {
                "id": "8",
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Ndolé Riz",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "7",
                "ratings": "[]",
                "category": "dish",
                "country": "Nigeria",
                "description": "Test",
                "name": "Koki patate douce",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "6",
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet DG",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "5",
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Poulet braisé",
                "price": "11.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": True,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "4",
                "ratings": "[]",
                "category": "dish",
                "country": "Benin",
                "description": "Test",
                "name": "Okok manioc",
                "price": "15.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 1,
                    "firstname": "test",
                    "lastname": "test",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "3",
                "ratings": "[]",
                "category": "dish",
                "country": "Cameroun",
                "description": "Test",
                "name": "Eru fufu",
                "price": "15.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": True,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 4,
                    "firstname": "toutii",
                    "lastname": "N",
                    "acceptance_rate": 100.0,
                },
            },
            {
                "id": "2",
                "ratings": "[]",
                "category": "dish",
                "country": "Congo",
                "description": "Test",
                "name": "Gombo porc riz",
                "price": "13.0",
                "photo": "https://some-url.com",
                "is_enabled": True,
                "is_suitable_for_quick_delivery": False,
                "is_suitable_for_scheduled_delivery": False,
                "cooker": {
                    "id": 4,
                    "firstname": "toutii",
                    "lastname": "N",
                    "acceptance_rate": 100.0,
                },
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
                        "ratings": "[]",
                        "photo": "https://some-url.com",
                        "cooker": {
                            "acceptance_rate": 100.0,
                            "firstname": "toutii",
                            "id": 4,
                            "lastname": "N",
                        },
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
                        "cooker": {
                            "acceptance_rate": 100.0,
                            "firstname": "test",
                            "id": 1,
                            "lastname": "test",
                        },
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": True,
                        "ratings": "[]",
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
                        "cooker": {
                            "acceptance_rate": 100.0,
                            "firstname": "test",
                            "id": 1,
                            "lastname": "test",
                        },
                        "country": "Cameroun",
                        "description": "Test",
                        "id": "5",
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": False,
                        "is_suitable_for_scheduled_delivery": True,
                        "name": "Poulet braisé",
                        "photo": "https://some-url.com",
                        "price": "11.0",
                        "ratings": "[]",
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
