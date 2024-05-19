import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.parametrize(
    "query_parameter",
    [
        {"name": "pou"},
        {"sort": "new"},
        {"sort": "famous"},
    ],
    ids=[
        "search_by_name",
        "sort_by_new",
        "sort_by_famous",
    ],
)
class TestListDishesForCustomerSuccess:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
        query_parameter: dict,
    ) -> None:

        # Then we list the dishes
        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
            data=query_parameter,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("ok") is True
        assert response.json().get("status_code") == 200
        assert response.json().get("data")


class TestListDishesForCustomerWithMissingQueryParameter:
    @pytest.mark.django_db
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        customer_dish_path: str,
    ) -> None:

        # Then we list the dishes
        response = client.get(
            f"{customer_dish_path}",
            follow=False,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True, "status_code": 404}
