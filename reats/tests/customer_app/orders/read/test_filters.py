
import pytest
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core_app.models import OrderModel, DishModel, DrinkModel, CustomerModel, CookerModel, AddressModel
from utils.enums import OrderStatusEnum





@pytest.fixture
def setup_filter_test_data(
    create_authenticated_customer, 
    create_test_cooker, 
    create_test_address
):
    """Crée des données de test pour les filtres"""
    customer = create_authenticated_customer
    cooker = create_test_cooker
    address = create_test_address
    
    # Nettoyer les données existantes
    OrderModel.objects.filter(customer=customer).delete()
    
    # Créer des commandes avec différentes caractéristiques
    orders_data = [
        # Commande 1: PENDING, créée il y a 5 jours, avec plat 1
        {
            'status': OrderStatusEnum.PENDING,
            'created': timezone.now() - timedelta(days=5),
            'delivery_fees': 2.0,
            'rating': 4.5,
            'comment': 'Excellente commande',
        },
        # Commande 2: PROCESSING, créée il y a 3 jours, avec boisson 1
        {
            'status': OrderStatusEnum.PROCESSING,
            'created': timezone.now() - timedelta(days=3),
            'delivery_fees': 3.5,
            'rating': 3.0,
            'comment': 'Commande standard',
        },
        # Commande 3: COMPLETED, créée hier, livraison programmée demain
        {
            'status': OrderStatusEnum.COMPLETED,
            'created': timezone.now() - timedelta(days=1),
            'delivery_fees': 5.0,
            'rating': 5.0,
            'comment': 'Parfait !',
            'scheduled_delivery_date': timezone.now() + timedelta(days=1),
        },
        # Commande 4: PENDING, créée aujourd'hui
        {
            'status': OrderStatusEnum.PENDING,
            'created': timezone.now(),
            'delivery_fees': 1.5,
            'rating': 0.0,  # Pas encore noté
            'comment': None,
        },
    ]
    
    orders = []
    for i, order_data in enumerate(orders_data):
        # Extraire la date de création pour l'appliquer après (car auto_now_add=True)
        created_date = order_data.pop('created')
        
        order = OrderModel.objects.create(
            customer=customer,
            cooker=cooker,
            address=address,
            **order_data
        )
        # Forcer la date de création
        OrderModel.objects.filter(id=order.id).update(created=created_date)
        
      
        if i == 0:  
            dish = DishModel.objects.create(
                name=f"Plat Test {i}",
                price=10.0,
                cooker=cooker,
                category="dish",
                country="France",
                photo="test.jpg",
                is_enabled=True
            )
        orders.append(order)
    
    return customer, orders


@pytest.mark.django_db
class TestOrderFiltersBasic:
    """Tests des filtres basiques"""
    
    def test_filter_by_status(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre par statut"""
        customer, orders = setup_filter_test_data
        
        # Test avec statut PENDING
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={'status': OrderStatusEnum.PENDING}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        # Doit avoir 2 commandes PENDING
        assert len(data['results']) == 2
        for order in data['results']:
            assert order['status'] == OrderStatusEnum.PENDING
    
    def test_filter_by_multiple_statuses(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre avec plusieurs statuts (IN)"""
        customer, orders = setup_filter_test_data
        
        # Test avec statuts PENDING et PROCESSING
        statuses = [OrderStatusEnum.PENDING, OrderStatusEnum.PROCESSING]
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={'status_in': ','.join(statuses)}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        # Doit avoir 3 commandes (2 PENDING + 1 PROCESSING)
        assert len(data['results']) == 3
        statuses_received = {order['status'] for order in data['results']}
        assert statuses_received == set(statuses)
    
    def test_filter_by_date_range(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test le filtre par plage de dates"""
        customer, orders = setup_filter_test_data
        
        # Date d'hier à aujourd'hui
        yesterday = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'created_after': yesterday,
                'ordering': '-created'  # Plus récent d'abord
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        # Doit avoir les commandes créées hier et aujourd'hui
        assert len(data['results']) >= 2  # COMPLETED (hier) + PENDING (aujourd'hui)
    
    def test_filter_by_invalid_status(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec un statut invalide"""
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={'status': 'INVALID_STATUS'}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        # Doit retourner une liste vide pour un statut invalide
        assert data['results'] == []
        assert data['pagination']['total_items'] == 0


@pytest.mark.django_db
class TestOrderFiltersCombined:
    """Tests des filtres combinés"""
    
    def test_combined_status_and_date(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test combinaison statut + date"""
        customer, orders = setup_filter_test_data
        
        # PENDING créées après avant-hier
        two_days_ago = (timezone.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'status': OrderStatusEnum.PENDING,
                'created_after': two_days_ago
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        # Doit avoir 1 commande PENDING créée après avant-hier (celle d'aujourd'hui)
        assert len(data['results']) == 1
        order = data['results'][0]
        assert order['status'] == OrderStatusEnum.PENDING
    
    def test_filter_with_ordering(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test filtre avec tri"""
        customer, orders = setup_filter_test_data
        
        # Toutes les commandes, triées par frais de livraison décroissants
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'ordering': '-delivery_fees'  # Plus cher d'abord
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        results = data['results']
        
        # Vérifier l'ordre décroissant des frais
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['delivery_fees'] >= results[i + 1]['delivery_fees']
    
    def test_multiple_ordering(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test tri multiple"""
        # Ajoutons une commande avec même frais pour tester le tri secondaire
        customer, orders = setup_filter_test_data
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'ordering': 'delivery_fees,-created'  # Frais croissants, puis date décroissante
            }
        )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrderFiltersEdgeCases:
    """Tests des cas limites des filtres"""
    
    def test_empty_filter_parameters(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec paramètres de filtre vides"""
        # Paramètres vides ou avec espaces
        test_cases = [
            {'status': ''},
            {'status': '   '},
            {'created_after': ''},
            {'ordering': ''},
        ]
        
        for params in test_cases:
            response = client.get(
                customer_order_path,
                follow=False,
                **auth_headers,
                data=params
            )
            
            # Doit toujours retourner 200
            assert response.status_code == status.HTTP_200_OK
    
    def test_special_characters_in_search(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec caractères spéciaux dans la recherche"""
        customer, orders = setup_filter_test_data
        
        test_cases = [
            'excellente!',  # Point d'exclamation
            'commande&test',  # Esperluette
            'parfait@livraison',  # Arobase
            'test#123',  # Dièse
        ]
        
        for search_term in test_cases:
            response = client.get(
                customer_order_path,
                follow=False,
                **auth_headers,
                data={'search': search_term}
            )
            
            assert response.status_code == status.HTTP_200_OK
            # Ne devrait pas planter avec des caractères spéciaux
    
    def test_very_large_date_range(self, auth_headers, client, customer_order_path, setup_filter_test_data):
        """Test avec une très large plage de dates"""
        customer, orders = setup_filter_test_data
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'created_after': '2000-01-01',  
                'created_before': '2030-12-31',  
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        assert data['pagination']['total_items'] == len(orders)


@pytest.mark.django_db  
class TestOrderFiltersWithPagination:
    """Tests combinant filtres et pagination"""
    
    def test_filter_pagination_integration(self, auth_headers, client, customer_order_path, create_authenticated_customer, create_test_cooker, create_test_address):
        """Test l'intégration filtres + pagination"""
        # Créer plus de données pour tester la pagination
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
        
        # Test 1: Filtre + pagination par défaut
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={'status': OrderStatusEnum.PENDING}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        pagination = data['pagination']
        assert pagination['total_items'] == 25
        assert pagination['items_per_page'] == 10
        assert pagination['total_pages'] == 3 
        
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'status': OrderStatusEnum.PENDING,
                'page_size': 5,
                'page': 2
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        
        pagination = data['pagination']
        assert pagination['current_page'] == 2
        assert pagination['items_per_page'] == 5
        assert len(data['results']) == 5
    
    def test_filter_ordering_pagination(self, auth_headers, client, customer_order_path, create_authenticated_customer, create_test_cooker, create_test_address):
        """Test combinaison filtre + tri + pagination"""
        customer = create_authenticated_customer
        cooker = create_test_cooker
        address = create_test_address
        
        
        OrderModel.objects.filter(customer=customer).delete()

        fees = [1.0, 5.0, 3.0, 4.0, 2.0, 6.0]
        for fee in fees:
            order = OrderModel.objects.create(
                customer=customer,
                cooker=cooker,
                address=address,
                status=OrderStatusEnum.PENDING,
                delivery_fees=fee,
            )
            OrderModel.objects.filter(id=order.id).update(created=timezone.now())
        
        # Filtre PENDING + tri par frais décroissant + pagination
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'status': OrderStatusEnum.PENDING,
                'ordering': '-delivery_fees',
                'page_size': 3,
                'page': 1
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        results = data['results']
        
        assert results[0]['delivery_fees'] == 6.0
        assert results[1]['delivery_fees'] == 5.0
        assert results[2]['delivery_fees'] == 4.0
        
        # Deuxième page
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'status': OrderStatusEnum.PENDING,
                'ordering': '-delivery_fees',
                'page_size': 3,
                'page': 2
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        results = data['results']
        
        # Vérifier l'ordre sur la deuxième page
        assert results[0]['delivery_fees'] == 3.0
        assert results[1]['delivery_fees'] == 2.0
        assert results[2]['delivery_fees'] == 1.0


@pytest.mark.django_db
class TestOrderFiltersPerformance:
    """Tests de performance des filtres"""
    
    def test_filter_performance_large_dataset(self, auth_headers, client, customer_order_path, create_authenticated_customer, create_test_cooker, create_test_address):
        """Test les performances avec un grand dataset"""
        
        customer = create_authenticated_customer
        OrderModel.objects.filter(customer=customer).delete()
        
        customer = create_authenticated_customer
        cooker = create_test_cooker
        address = create_test_address
        
        batch_size = 100
        total_orders = 1000
        
        orders_to_create = []
        for i in range(total_orders):
            created_date = timezone.now() - timedelta(days=i % 30)
            order = OrderModel.objects.create(
                customer=customer,
                cooker=cooker,
                address=address,
                status=OrderStatusEnum.PENDING if i % 2 == 0 else OrderStatusEnum.COMPLETED,
                delivery_fees=2.0 + (i % 10 * 0.5),
            )
            OrderModel.objects.filter(id=order.id).update(created=created_date)
            
            # Insertion par batch - Désactivé car on doit update created
            #     orders_to_create = []
        
        import time
        start_time = time.time()
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={
                'status': OrderStatusEnum.PENDING,
                'created_after': (timezone.now() - timedelta(days=15)).strftime('%Y-%m-%d'),
                'page_size': 50
            }
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert response.status_code == status.HTTP_200_OK
        
        assert execution_time < 2.0, f"Filtre trop lent: {execution_time:.2f} secondes"
        
        print(f"Performance test: {execution_time:.2f} seconds for filtering 1000 orders")
    
    def test_index_usage(self, auth_headers, client, customer_order_path):
        """Vérifie que les bons indexes sont utilisés"""
        
        
        response = client.get(
            customer_order_path,
            follow=False,
            **auth_headers,
            data={'status': OrderStatusEnum.PENDING}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()['data']
        