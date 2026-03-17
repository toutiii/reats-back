import time
from datetime import timedelta

import pytest
from core_app.models import DishModel, OrderDishItemModel, OrderModel
from django.utils import timezone
from rest_framework import status
from utils.enums import ErrorCodeEnum, OrderStatusEnum


@pytest.fixture
def setup_filter_test_data(create_authenticated_customer, create_test_cooker, create_test_address):
    """Crée des données de test pour les filtres"""
    customer = create_authenticated_customer
    cooker = create_test_cooker
    address = create_test_address

    # Nettoyer toutes les commandes existantes pour ce client
    OrderModel.objects.filter(customer=customer).delete()

    # Créer 4 commandes de test en utilisant les objets de fixtures
    orders = []

    order_configs = [
        {"status": OrderStatusEnum.PENDING, "created_delta": 5, "fees": 2.0, "rating": 4.5},
        {"status": OrderStatusEnum.PROCESSING, "created_delta": 3, "fees": 3.5, "rating": 3.0},
        {"status": OrderStatusEnum.COMPLETED, "created_delta": 1, "fees": 5.0, "rating": 5.0, "scheduled": 1},
        {"status": OrderStatusEnum.PENDING, "created_delta": 0, "fees": 1.5, "rating": 0.0},
    ]

    for config in order_configs:
        created_date = timezone.now() - timedelta(days=config["created_delta"])

        order_data = {
            "customer": customer,
            "cooker": cooker,
            "address": address,
            "status": config["status"],
            "delivery_fees": config["fees"],
            "rating": config["rating"],
        }

        if "scheduled" in config:
            order_data["scheduled_delivery_date"] = timezone.now() + timedelta(days=config["scheduled"])

        order = OrderModel.objects.create(**order_data)
        # Forcer la date de création (car auto_now_add=True)
        OrderModel.objects.filter(id=order.id).update(created=created_date)
        order.refresh_from_db()
        orders.append(order)

    # Création du plat pour la première commande (pour tests Dish)
    DishModel.objects.get_or_create(
        name="Plat Test 0",
        price=10.0,
        cooker=cooker,
        category="dish",
        country="France",
        is_enabled=True,
    )

    return customer, orders


@pytest.mark.django_db
class TestOrderFiltersBasic:
    """Tests des filtres basiques"""

    def test_filter_by_status(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre par statut"""
        customer, orders = setup_filter_test_data

        # Test avec statut PENDING
        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Doit avoir 2 commandes PENDING
        assert len(data["results"]) == 2
        for order in data["results"]:
            assert order["status"] == OrderStatusEnum.PENDING

    def test_filter_by_multiple_statuses(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre avec plusieurs statuts (IN)"""
        customer, orders = setup_filter_test_data

        # Test avec statuts PENDING et PROCESSING
        statuses = [OrderStatusEnum.PENDING, OrderStatusEnum.PROCESSING]
        response = client.get(customer_order_path, follow=False, **auth_headers, data={"status_in": ",".join(statuses)})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Doit avoir 3 commandes (2 PENDING + 1 PROCESSING)
        assert len(data["results"]) == 3
        statuses_received = {order["status"] for order in data["results"]}
        assert statuses_received == set(statuses)

    def test_filter_by_date_range(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre par plage de dates"""
        customer, orders = setup_filter_test_data

        # Date d'hier à aujourd'hui
        yesterday = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"created_after": yesterday, "ordering": "-created"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        # Doit avoir les commandes créées hier et aujourd'hui
        assert len(data["results"]) >= 2  # COMPLETED (hier) + PENDING (aujourd'hui)

    def test_filter_by_invalid_status(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec un statut invalide"""
        response = client.get(customer_order_path, follow=False, **auth_headers, data={"status": "INVALID_STATUS"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert data["results"] == []
        assert data["pagination"]["total_items"] == 0


@pytest.mark.django_db
class TestOrderFiltersCombined:
    """Tests des filtres combinés"""

    def test_combined_status_and_date(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test combinaison statut + date"""
        customer, orders = setup_filter_test_data

        # PENDING créées après avant-hier
        two_days_ago = (timezone.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "created_after": two_days_ago},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert len(data["results"]) == 1
        order = data["results"][0]
        assert order["status"] == OrderStatusEnum.PENDING

    def test_filter_with_ordering(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test filtre avec tri"""
        customer, orders = setup_filter_test_data

        response = client.get(customer_order_path, follow=False, **auth_headers, data={"ordering": "-delivery_fees"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        results = data["results"]

        # Vérifier l'ordre décroissant des frais
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["delivery_fees"] >= results[i + 1]["delivery_fees"]

    def test_multiple_ordering(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test tri multiple"""
        # Ajoutons une commande avec même frais pour tester le tri secondaire
        customer, orders = setup_filter_test_data

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                "ordering": "delivery_fees,-created"  # Frais croissants, puis date décroissante
            },
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrderFiltersEdgeCases:
    """Tests des cas limites des filtres"""

    def test_empty_filter_parameters(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec paramètres de filtre vides"""
        # Paramètres vides ou avec espaces
        test_cases = [
            {"status": ""},
            {"status": "   "},
            {"created_after": ""},
            {"ordering": ""},
        ]

        for params in test_cases:
            response = client.get(customer_order_path, follow=False, **auth_headers, data=params)

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "search_term",
        [
            "excellente!",  # Point d'exclamation
            "commande&test",  # Esperluette
            "parfait@livraison",  # Arobase
            "test#123",  # Dièse
            "test<script>",  # Balise HTML
            "test;DROP",  # Point-virgule (SQL-like)
            "test|command",  # Pipe
            "test$variable",  # Dollar
        ],
        ids=[
            "exclamation",
            "ampersand",
            "at_sign",
            "hash",
            "html_tag",
            "semicolon_sql_like",
            "pipe",
            "dollar",
        ],
    )
    def test_special_characters_rejected_in_search(
        self, auth_headers, client, customer_order_path, setup_filter_test_data, search_term
    ):
        """Test que les caractères spéciaux (rejetés) retournent bien HTTP 400"""
        setup_filter_test_data  # ensures data exists (even if not used directly)

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"search": search_term},
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Expected 400 for '{search_term}', got {response.status_code}"

        response_data = response.json()
        assert not response_data.get("success", True), "Success should be False for invalid input"

    @pytest.mark.parametrize(
        "search_term",
        [
            "excellente",  # Lettres simples
            "très bon",  # Accents français
            "commande-test",  # Tiret
            "l'ordre",  # Apostrophe
            "test 123",  # Chiffres et espaces
        ],
        ids=[
            "simple_letters",
            "french_accents",
            "dash",
            "apostrophe",
            "digits_and_spaces",
        ],
    )
    def test_valid_characters_accepted_in_search(
        self, auth_headers, client, customer_order_path, setup_filter_test_data, search_term
    ):
        """Test que les caractères valides sont acceptés avec HTTP 200"""
        setup_filter_test_data  # ensures data exists (even if not used directly)

        response = client.get(customer_order_path, follow=False, **auth_headers, data={"search": search_term})

        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Expected 200 for '{search_term}', got {response.status_code}"

    def test_created_after_too_old_rejected(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test qu'une date trop ancienne (3 ans) est rejetée avec HTTP 400"""
        customer, orders = setup_filter_test_data

        # 3 ans en arrière
        three_years_ago = (timezone.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"created_after": three_years_ago}
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Expected 400 for date older than 2 years ({three_years_ago}), got {response.status_code}"

        response_data = response.json()

        errors = response_data.get("error", {}).get("details", {})
        if not errors:
            errors = response_data

        assert "created_after" in errors, f"Error details should contain 'created_after', got: {response_data}"

    def test_created_after_recent_accepted(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test qu'une date récente (1 an) est acceptée avec HTTP 200"""
        customer, orders = setup_filter_test_data

        one_year_ago = (timezone.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        response = client.get(customer_order_path, follow=False, **auth_headers, data={"created_after": one_year_ago})

        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Expected 200 for recent date ({one_year_ago}), got {response.status_code}"


@pytest.mark.django_db
class TestOrderFiltersWithPagination:
    """Tests combinant filtres et pagination"""

    @pytest.fixture
    def setup_pagination_data(
        self,
        create_authenticated_customer,
        create_test_cooker,
        create_test_address,
    ):
        """Fixture pour créer les données de pagination"""
        customer = create_authenticated_customer
        cooker = create_test_cooker
        address = create_test_address

        OrderModel.objects.filter(customer=customer).delete()
        for i in range(25):
            created_date = timezone.now() - timedelta(days=i)
            order = OrderModel.objects.create(
                customer=customer,
                cooker=cooker,
                address=address,
                status=OrderStatusEnum.PENDING,
                delivery_fees=2.0 + (i * 0.1),
            )
            OrderModel.objects.filter(id=order.id).update(created=created_date)
        return customer

    def test_filter_pagination_default(
        self,
        auth_headers,
        client,
        customer_order_path,
        setup_pagination_data,
    ):
        """Test filtre + pagination par défaut"""
        # Test 1: Filtre + pagination par défaut
        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"status": OrderStatusEnum.PENDING}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        pagination = data["pagination"]
        assert pagination["total_items"] == 25
        assert pagination["items_per_page"] == 10
        assert pagination["total_pages"] == 3

    def test_filter_pagination_custom(
        self,
        auth_headers,
        client,
        customer_order_path,
        setup_pagination_data,
    ):
        """Test filtre + pagination custom"""
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "page_size": 5, "page": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        pagination = data["pagination"]
        assert pagination["current_page"] == 2
        assert pagination["items_per_page"] == 5
        assert len(data["results"]) == 5

    def test_filter_ordering_pagination(
        self,
        auth_headers,
        client,
        customer_order_path,
        create_authenticated_customer,
        create_test_cooker,
        create_test_address,
    ):
        """Test combinaison filtre + tri + pagination"""
        customer = create_authenticated_customer
        cooker = create_test_cooker
        address = create_test_address

        OrderModel.objects.filter(customer=customer).delete()

        fees = [1.0, 5.0, 3.0, 4.0, 2.0, 6.0]
        orders = [
            OrderModel(
                customer=customer,
                cooker=cooker,
                address=address,
                status=OrderStatusEnum.PENDING,
                delivery_fees=fee,
            )
            for fee in fees
        ]
        OrderModel.objects.bulk_create(orders)

        # Filtre PENDING + tri par frais décroissant + pagination
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "ordering": "-delivery_fees", "page_size": 3, "page": 1},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        results = data["results"]

        assert results[0]["delivery_fees"] == 6.0
        assert results[1]["delivery_fees"] == 5.0
        assert results[2]["delivery_fees"] == 4.0

        # Deuxième page
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={"status": OrderStatusEnum.PENDING, "ordering": "-delivery_fees", "page_size": 3, "page": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        results = data["results"]

        # Vérifier l'ordre sur la deuxième page
        assert results[0]["delivery_fees"] == 3.0
        assert results[1]["delivery_fees"] == 2.0
        assert results[2]["delivery_fees"] == 1.0


@pytest.mark.django_db
class TestOrderFiltersPerformance:
    """Tests de performance des filtres"""

    def test_filter_performance_large_dataset(
        self,
        auth_headers,
        client,
        customer_order_path,
        create_authenticated_customer,
        create_test_cooker,
        create_test_address,
    ):
        """Test les performances avec un grand dataset"""

        customer = create_authenticated_customer
        OrderModel.objects.filter(customer=customer).delete()

        customer = create_authenticated_customer
        cooker = create_test_cooker
        address = create_test_address

        total_orders = 1000
        orders = []
        for i in range(total_orders):
            created_date = timezone.now() - timedelta(days=i % 30)
            orders.append(
                OrderModel(
                    customer=customer,
                    cooker=cooker,
                    address=address,
                    status=OrderStatusEnum.PENDING if i % 2 == 0 else OrderStatusEnum.COMPLETED,
                    delivery_fees=2.0 + (i % 10 * 0.5),
                    created=created_date,
                    modified=created_date,
                )
            )
        OrderModel.objects.bulk_create(orders)

        start_time = time.time()

        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                "status": OrderStatusEnum.PENDING,
                "created_after": (timezone.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
                "page_size": 50,
            },
        )

        end_time = time.time()
        execution_time = end_time - start_time

        assert response.status_code == status.HTTP_200_OK

        assert execution_time < 2.0, f"Filtre trop lent: {execution_time:.2f} secondes"

        print(f"Performance test: {execution_time:.2f} seconds for filtering 1000 orders")


@pytest.mark.django_db
class TestOrderFiltersTotalAmount:
    """Tests des filtres par montant total"""

    def test_filter_min_total(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test filtre par montant minimum"""
        customer, orders = setup_filter_test_data

        # Modifier les prix/quantités pour avoir des totaux connus
        # Commande 1: delivery=2.0, plat 1 (prix 10.0) -> total = 12.0
        # Nous allons tricher un peu et créer des OrderDishItem pour ces commandes pour avoir des totaux

        dish = DishModel.objects.get(name="Plat Test 0")

        # Commande 1 (index 0): Total = 2.0 (installé) + 10.0 (plat) = 12.0
        OrderDishItemModel.objects.create(order=orders[0], dish=dish, dish_quantity=1)

        # Commande 2 (index 1): Total = 3.5 (installé) + 20.0 (2 plats) = 23.5
        OrderDishItemModel.objects.create(order=orders[1], dish=dish, dish_quantity=2)

        # Commande 3 (index 2): Total = 5.0 (installé) = 5.0 (sans articles)

        # Test min_total = 15.0 (devrait retourner que la commande 2)
        response = client.get(customer_order_path, follow=False, **auth_headers, data={"min_total": 15.0})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == orders[1].id

    def test_filter_max_total(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test filtre par montant maximum"""
        customer, orders = setup_filter_test_data

        dish = DishModel.objects.get(name="Plat Test 0")
        print(f"DEBUG: Dish Price = {dish.price}")

        # Commande 1: Total 12.0
        OrderDishItemModel.objects.create(order=orders[0], dish=dish, dish_quantity=1)
        # Commande 2: Total 23.5
        OrderDishItemModel.objects.create(order=orders[1], dish=dish, dish_quantity=2)

        # Test max_total = 15.0 (devrait retourner commande 1 et les autres petites commandes)
        response = client.get(customer_order_path, follow=False, **auth_headers, data={"max_total": 15.0})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        print(f"DEBUG: Response Results = {data['results']}")

        # Résultats attendus : Commande 1 (12.0), Commande 3 (5.0), Commande 4 (1.5)
        # La Commande 2 (23.5) doit être exclue
        ids = [order["id"] for order in data["results"]]
        assert orders[1].id not in ids
        assert orders[0].id in ids

    def test_filter_min_and_max_total(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test filtre combiné min et max"""
        customer, orders = setup_filter_test_data

        dish = DishModel.objects.get(name="Plat Test 0")

        # Commande 1: Total 12.0
        OrderDishItemModel.objects.create(order=orders[0], dish=dish, dish_quantity=1)
        # Commande 2: Total 23.5
        OrderDishItemModel.objects.create(order=orders[1], dish=dish, dish_quantity=2)
        # Commande 3: Total 5.0

        # Test range 10.0 - 20.0 (devrait retourner que Commande 1)
        response = client.get(
            customer_order_path, follow=False, **auth_headers, data={"min_total": 10.0, "max_total": 20.0}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]

        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == orders[0].id


@pytest.mark.django_db
class TestOrderHistoryFilter:
    """Tests spécifiques pour OrderHistoryFilter"""

    def test_history_filter_total_amount(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre de montant total spécifiquement pour l'historique"""

        from core_app.models import DishModel, OrderModel
        from utils.filters import OrderFilter

        customer, orders = setup_filter_test_data

        dish = DishModel.objects.get(name="Plat Test 0")
        # Commande 1: Total 12.0
        OrderDishItemModel.objects.create(order=orders[0], dish=dish, dish_quantity=1)

        qs = OrderModel.objects.all()

        # Test direct du FilterSet pour être sûr de tester la correction du bug
        f = OrderFilter(data={"min_total_amount": 10.0}, queryset=qs)
        result_qs = f.qs

        assert result_qs.count() >= 1
        assert orders[0] in result_qs

    def test_history_filter_dates_aliases(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test les alias start_date et end_date pour la compatibilité descendante"""
        from datetime import timedelta

        from core_app.models import OrderModel
        from django.utils import timezone
        from utils.filters import OrderFilter

        customer, orders = setup_filter_test_data

        qs = OrderModel.objects.all()

        yesterday = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Test start_date (created_after)
        f = OrderFilter(data={"start_date": yesterday}, queryset=qs)
        # Devrait inclure la commande d'aujourd'hui et celle d'hier, exclure celle d'il y a 5 jours
        assert f.qs.count() >= 2

        # Test end_date (created_before)
        f = OrderFilter(data={"end_date": yesterday}, queryset=qs)
        # Devrait inclure les vieilles commandes
        assert f.qs.count() >= 1

    def test_history_filter_validation_error(self, auth_headers, client, customer_order_history_path):
        """Test que la validation explicite des dates retourne bien une erreur 400"""

        # Cas 1: start > end
        response = client.get(
            customer_order_history_path,
            follow=False,
            **auth_headers,
            data={"start_date": "2024-01-02", "end_date": "2024-01-01"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()

        # Gestion du format d'erreur standardisé {"error": {"code": ...}}
        assert "error" in data
        assert "code" in data.get("error", {})
        assert data.get("error", {}).get("code") == ErrorCodeEnum.VALIDATION_ERROR
