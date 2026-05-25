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
            status=OrderStatusEnum.ACCEPTED,
            delivery_fees=2.4,
            created=datetime.now() - timedelta(days=i),
            modified=datetime.now() - timedelta(days=i),
        )
        orders.append(order)

    return customer, orders


@pytest.mark.django_db
class TestOrdersPaginationScenarios:
    @pytest.mark.parametrize(
        ("payload", "expected_status", "expected_page", "expected_page_size"),
        [
            # Défaut: page 1, taille 10
            ({"status": OrderStatusEnum.PENDING}, status.HTTP_200_OK, 1, 10),
            # page_size dépasse le maximum (100)
            ({"status": OrderStatusEnum.PENDING, "page_size": 500}, status.HTTP_200_OK, 1, 100),
            # page_size invalides (doivent retomber sur 10)
            ({"status": OrderStatusEnum.PENDING, "page_size": "abc"}, status.HTTP_200_OK, 1, 10),
            ({"status": OrderStatusEnum.PENDING, "page_size": ""}, status.HTTP_200_OK, 1, 10),
            # Pages hors limites ou invalides (doivent retourner 404)
            ({"status": OrderStatusEnum.PENDING, "page": 999}, status.HTTP_404_NOT_FOUND, None, None),
            ({"status": OrderStatusEnum.PENDING, "page": 0}, status.HTTP_404_NOT_FOUND, None, None),
            ({"status": OrderStatusEnum.PENDING, "page": -1}, status.HTTP_404_NOT_FOUND, None, None),
        ],
    )
    def test_pagination_scenarios(
        self,
        auth_headers,
        client,
        customer_order_path,
        customer_with_30_orders,
        payload,
        expected_status,
        expected_page,
        expected_page_size,
    ):
        """Vérifie divers scénarios de pagination (valeurs par défaut, limites, erreurs)"""
        customer, orders = customer_with_30_orders
        response = client.get(customer_order_path, follow=False, **auth_headers, data=payload)

        assert response.status_code == expected_status

        if expected_status == status.HTTP_200_OK:
            data = response.json().get("data", {})
            pagination = data["pagination"]
            assert pagination["current_page"] == expected_page
            assert pagination["items_per_page"] == expected_page_size
            assert len(data["results"]) <= expected_page_size

    def test_second_page_with_enough_data(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        """
        Vérifie que la pagination fonctionne sur plusieurs pages
        et que les éléments ne se recoupent pas entre pages.
        """
        customer, orders = customer_with_30_orders
        response_page1 = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING, "page_size": 5}
        )
        assert response_page1.status_code == status.HTTP_200_OK
        data1 = response_page1.json().get("data", {})
        pagination1 = data1["pagination"]
        results1 = data1["results"]
        assert pagination1.get("total_pages", 0) > 1, "Should have enough data for multiple pages"

        response_page2 = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page_size": 5, "page": 2},
        )
        assert response_page2.status_code == status.HTTP_200_OK
        data_from_response_page2 = response_page2.json().get("data", {})
        pagination_from_response_page2 = data_from_response_page2["pagination"]
        results_from_response_page_2 = data_from_response_page2["results"]
        assert pagination1["current_page"] == 1
        assert pagination_from_response_page2["current_page"] == 2
        ids_page1 = {order["id"] for order in results1}
        ids_page2 = {order["id"] for order in results_from_response_page_2}
        assert ids_page1.isdisjoint(ids_page2), "Les pages doivent avoir des éléments différents"

    def test_few_data_less_than_page_size(self, auth_headers, client, customer_order_path, customer_with_few_orders):
        """Vérifie que la pagination retourne tous les éléments si leur nombre est inférieur au page_size."""
        customer, orders = customer_with_few_orders
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.ACCEPTED, "page_size": 10},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data", {})
        pagination = data["pagination"]
        results = data["results"]
        assert pagination["total_pages"] == 1
        assert pagination["current_page"] == 1
        assert pagination["total_items"] == len(orders)
        assert len(results) == len(orders)

    def test_no_orders_for_filter(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        """Vérifie que la pagination retourne une liste vide si aucun élément ne correspond au filtre."""
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

    def test_combination_page_and_page_size(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        """
        Vérifie que la pagination retourne les bons éléments pour une combinaison page/page_size donnée
        et respecte l'ordre demandé.
        """
        customer, orders = customer_with_30_orders
        orders_sorted = list(
            OrderModel.objects.filter(customer=customer, status=OrderStatusEnum.PENDING)
            .order_by("-modified")
            .values_list("id", flat=True)
        )
        page_size = 5
        page = 3
        assert len(orders_sorted) > page_size * (
            page - 1
        ), f"Not enough data for page {page} with page_size {page_size}"
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page": page, "page_size": page_size, "ordering": "-modified"},
        )
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

    def test_order_respected_across_pages(self, auth_headers, client, customer_order_path, customer_with_30_orders):
        """Vérifie que l'ordre des éléments est respecté sur toutes les pages et qu'il n'y a pas de doublons."""
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
            assert response.status_code == status.HTTP_200_OK
            data = response.json().get("data", {})
            results = data["results"]
            page_ids = [order["id"] for order in results]
            all_retrieved_ids.extend(page_ids)
        assert set(all_retrieved_ids) == set(expected_order_ids)
        assert all_retrieved_ids == expected_order_ids
        assert len(all_retrieved_ids) == len(set(all_retrieved_ids))

    def test_total_items_consistent_across_pages(
        self, auth_headers, client, customer_order_path, customer_with_30_orders
    ):
        """
        Vérifie que le champ total_items reste constant sur toutes les pages
        et correspond au nombre réel d'éléments filtrés.
        """
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
