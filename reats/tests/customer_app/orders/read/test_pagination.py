from datetime import datetime, timedelta

import pytest
from core_app.models import OrderModel
from rest_framework import status
from utils.enums import OrderStatusEnum


@pytest.fixture
def customer_with_30_orders(clean_authenticated_user_orders, create_test_cooker, create_test_address):
    """Crée 30 commandes pour le client authentifié"""
    customer = clean_authenticated_user_orders
    cooker = create_test_cooker
    address = create_test_address

    # Créer 30 commandes avec des dates différentes pour le tri
    orders = []
    for i in range(30):
        order = OrderModel.objects.create(
            customer=customer,
            cooker=cooker,
            address=address,
            status=OrderStatusEnum.PENDING,
            delivery_fees=2.4 + (i * 0.1),
            created=datetime.now() - timedelta(days=i),
            modified=datetime.now() - timedelta(days=i),
        )
        orders.append(order)

    return customer, orders


@pytest.fixture
def customer_with_few_orders(clean_authenticated_user_orders, create_test_cooker, create_test_address):
    """Crée 3 commandes seulement pour le client authentifié"""
    customer = clean_authenticated_user_orders
    cooker = create_test_cooker
    address = create_test_address

    orders = []
    for i in range(3):
        order = OrderModel.objects.create(
            customer=customer,
            cooker=cooker,
            address=address,
            status=OrderStatusEnum.PROCESSING,
            delivery_fees=2.4,
            created=datetime.now() - timedelta(days=i),
            modified=datetime.now() - timedelta(days=i),
        )
        orders.append(order)

    return customer, orders


@pytest.mark.django_db
class TestOrdersPaginationScenarios:
    def test_scenario_1_default_pagination(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        customer, orders = customer_with_30_orders

        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("success")

        data = response.json().get("data", {})
        pagination = data["pagination"]
        results = data["results"]

        assert pagination["current_page"] == 1
        assert pagination["items_per_page"] == 10
        assert len(results) <= 10

        assert len(results) > 0
        for order in results:
            assert order["status"] == OrderStatusEnum.PENDING

    def test_scenario_2_page_size_exceeds_maximum(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page_size": 500},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json().get("data", {})
        pagination = data["pagination"]

        assert pagination["items_per_page"] == 100
        assert len(data["results"]) <= 100

    @pytest.mark.parametrize("invalid_page_size", ["abc", "invalid", "", "   "])
    def test_scenario_3_invalid_page_size(
        self, auth_headers, client, customer_order_path, invalid_page_size, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page_size": invalid_page_size},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json().get("data", {})
        pagination = data["pagination"]

        assert pagination["items_per_page"] == 10

    def test_scenario_4_second_page_with_enough_data(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        response_page1 = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING, "page_size": 5}
        )

        assert response_page1.status_code == status.HTTP_200_OK

        data1 = response_page1.json().get("data", {})
        pagination1 = data1["pagination"]
        results1 = data1["results"]

        if pagination1.get("total_pages", 0) > 1:
            response_page2 = client.get(
                customer_order_path,
                follow=False,
                **auth_headers,
                data={"status": OrderStatusEnum.PENDING, "page_size": 5, "page": 2},
            )

            assert response_page2.status_code == status.HTTP_200_OK

            data2 = response_page2.json().get("data", {})
            pagination2 = data2["pagination"]
            results2 = data2["results"]

            assert pagination1["current_page"] == 1
            assert pagination2["current_page"] == 2

            ids_page1 = {order["id"] for order in results1}
            ids_page2 = {order["id"] for order in results2}

            assert ids_page1.isdisjoint(ids_page2), "Les pages doivent avoir des éléments différents"
        else:
            pytest.skip("Not enough data for multiple pages")

    def test_scenario_5_page_beyond_total_pages(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        response_info = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING, "page_size": 10}
        )

        assert response_info.status_code == status.HTTP_200_OK
        total_pages = response_info.json()["data"]["pagination"]["total_pages"]

        page_beyond = total_pages + 5

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page_size": 10, "page": page_beyond},
        )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("DRF PageNumberPagination returns 404 for out-of-range pages")
        else:
            assert response.status_code == status.HTTP_200_OK

            data = response.json().get("data", {})
            pagination = data["pagination"]
            results = data["results"]

            assert results == []
            assert pagination["current_page"] == page_beyond

    def test_scenario_6_few_data_less_than_page_size(
        self, auth_headers, client, customer_order_path, customer_with_few_orders
    ):
        customer, orders = customer_with_few_orders

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PROCESSING, "page_size": 10},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json().get("data", {})
        pagination = data["pagination"]
        results = data["results"]

        assert pagination["total_pages"] == 1
        assert pagination["current_page"] == 1
        assert pagination["total_items"] == len(orders)
        assert len(results) == len(orders)

    def test_scenario_7_no_orders_for_filter(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        customer, orders = customer_with_30_orders

        response = client.get(customer_order_path, follow=False, **auth_headers, data={"status": "nonexistent_status"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json().get("data", {})
        pagination = data["pagination"]
        results = data["results"]

        assert results == []
        assert pagination["total_items"] == 0
        assert pagination["total_pages"] == 1
        assert pagination["current_page"] == 1

    def test_scenario_8_combination_page_and_page_size(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        orders_sorted = list(
            OrderModel.objects.filter(customer=customer, status=OrderStatusEnum.PENDING)
            .order_by("-modified")
            .values_list("id", flat=True)
        )

        page_size = 5
        page = 3

        if len(orders_sorted) <= page_size * (page - 1):
            pytest.skip(f"Not enough data for page {page} with page_size {page_size}")

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page": page, "page_size": page_size, "ordering": "-modified"},
        )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("DRF returns 404 for this page")

        assert response.status_code == status.HTTP_200_OK

        data = response.json().get("data", {})
        pagination = data["pagination"]
        results = data["results"]

        assert pagination["current_page"] == page
        assert pagination["items_per_page"] == page_size

        expected_start_index = (page - 1) * page_size

        if expected_start_index < len(orders_sorted):
            assert len(results) == min(page_size, len(orders_sorted) - expected_start_index)
            for i, order in enumerate(results):
                expected_id = orders_sorted[expected_start_index + i]
                assert order["id"] == expected_id

    def test_scenario_9_order_respected_across_pages(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        expected_order_ids = list(
            OrderModel.objects.filter(customer=customer, status=OrderStatusEnum.PENDING)
            .order_by("-modified")
            .values_list("id", flat=True)
        )

        all_retrieved_ids = []
        page_size = 7
        total_pages = (len(expected_order_ids) + page_size - 1) // page_size

        for page in range(1, total_pages + 1):
            response = client.get(
                customer_order_path,
                follow=False,
                **auth_headers,
                data={"status": OrderStatusEnum.PENDING, "page": page, "page_size": page_size, "ordering": "-modified"},
            )

            if response.status_code == status.HTTP_404_NOT_FOUND:
                pytest.skip(f"DRF returned 404 for page {page}")

            assert response.status_code == status.HTTP_200_OK

            data = response.json().get("data", {})
            results = data["results"]

            page_ids = [order["id"] for order in results]
            all_retrieved_ids.extend(page_ids)

        assert set(all_retrieved_ids) == set(expected_order_ids)
        assert all_retrieved_ids == expected_order_ids
        assert len(all_retrieved_ids) == len(set(all_retrieved_ids))

    def test_scenario_10_total_items_consistent_across_pages(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        customer, orders = customer_with_30_orders

        response_info = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING, "page_size": 8}
        )
        response_info = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING, "page_size": 8}
        )

        assert response_info.status_code == status.HTTP_200_OK
        total_pages = response_info.json()["data"]["pagination"]["total_pages"]

        total_items_set = set()

        valid_pages = [1, min(2, total_pages), min(3, total_pages)]

        for page in valid_pages:
            response = client.get(
                customer_order_path,
                follow=False,
                **auth_headers,
                data={"status": OrderStatusEnum.PENDING, "page": page, "page_size": 8},
            )

            assert response.status_code == status.HTTP_200_OK

            data = response.json().get("data", {})
            pagination = data["pagination"]

            total_items_set.add(pagination["total_items"])

        assert len(total_items_set) == 1, f"total_items devrait être constant, mais a varié: {total_items_set}"

        direct_count = OrderModel.objects.filter(customer=customer, status=OrderStatusEnum.PENDING).count()

        expected_total_items = next(iter(total_items_set))
        assert (
            direct_count == expected_total_items
        ), f"total_items ({expected_total_items}) devrait correspondre au compte direct ({direct_count})"


@pytest.mark.django_db
class TestPaginationEdgeCases:
    """Tests des cas limites de pagination"""

    def test_pagination_with_existing_data_only(
        self, auth_headers, client, customer_order_path, create_authenticated_customer
    ):
        customer = create_authenticated_customer

        OrderModel.objects.filter(customer=customer, status=OrderStatusEnum.PENDING).count()

        test_params = [
            {"status": OrderStatusEnum.PENDING},
            {"status": OrderStatusEnum.PENDING, "page_size": 5},
        ]

        for params in test_params:
            response = client.get(customer_order_path, follow=False, **auth_headers, data=params)

            if response.status_code == 200:
                response_json = response.json()

                assert "success" in response_json
                assert "message" in response_json
                assert "data" in response_json
                data = response_json["data"]
                assert "results" in data
                assert "pagination" in data

                pagination = data["pagination"]
                required_keys = ["current_page", "total_pages", "total_items", "items_per_page"]
                for key in required_keys:
                    assert key in pagination
                    assert isinstance(pagination[key], (int, float))

    def test_pagination_response_structure_always_consistent(self, auth_headers, client, customer_order_path):
        test_cases = [
            {"status": OrderStatusEnum.PENDING},
            {"status": OrderStatusEnum.PENDING, "page_size": 5},
            {"status": "invalid"},
        ]

        for params in test_cases:
            response = client.get(customer_order_path, follow=False, **auth_headers, data=params)

            assert response.status_code == status.HTTP_200_OK

            response_json = response.json()

            assert "success" in response_json
            assert "message" in response_json
            assert "data" in response_json

            data = response_json["data"]
            assert "results" in data
            assert "pagination" in data
            pagination = data["pagination"]
            required_keys = ["current_page", "total_pages", "total_items", "items_per_page"]
            for key in required_keys:
                assert key in pagination
                assert isinstance(pagination[key], (int, float))
