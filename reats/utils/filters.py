import django_filters
from django_filters import rest_framework as filters
from core_app.models import OrderModel
from utils.enums import OrderStatusEnum


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class OrderFilter(filters.FilterSet):
    status = django_filters.CharFilter(
        method='filter_status'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created', 
        lookup_expr='gte',
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created', 
        lookup_expr='lte',
    )
    
    modified_after = django_filters.DateTimeFilter(
        field_name='modified', 
        lookup_expr='gte'
    )
    
    min_total = django_filters.NumberFilter(
        method='filter_min_total',
    )
    
    max_total = django_filters.NumberFilter(
        method='filter_max_total',
    )
    
    cooker_id = django_filters.NumberFilter(
        field_name='cooker__id',
    )
    
    dish_id = django_filters.NumberFilter(
        method='filter_by_dish',
    )
    
    drink_id = django_filters.NumberFilter(
        method='filter_by_drink',
    )
    
    scheduled_date_after = django_filters.DateTimeFilter(
        field_name='scheduled_delivery_date',
        lookup_expr='gte'
    )
    
    scheduled_date_before = django_filters.DateTimeFilter(
        field_name='scheduled_delivery_date',
        lookup_expr='lte'
    )
    
    status_in = CharInFilter(
        field_name='status',
        lookup_expr='in',
    )
    
    search = django_filters.CharFilter(
        method='filter_search',
    )
    
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created', 'created'),
            ('modified', 'modified'),
            ('delivery_fees', 'delivery_fees'),
            ('scheduled_delivery_date', 'scheduled_date'),
        ),
    )
    
    class Meta:
        model = OrderModel
        fields = {
            'status': ['exact'],
            'created': ['gte', 'lte', 'gt', 'lt'],
            'delivery_fees': ['gte', 'lte'],
            'rating': ['gte', 'lte'],
        }
    
    def filter_status(self, queryset, name, value):
        """
        Filtre personnalisé pour le statut
        Gère les statuts invalides en retournant un queryset vide
        """
        if value not in dict(OrderStatusEnum.choices()):
            # Si le statut est invalide, retourne un queryset vide
            return queryset.none()
        
        return queryset.filter(status=value)
    
    def filter_min_total(self, queryset, name, value):
        """
        Filtre par montant total minimum
        Le montant total est calculé (delivery_fees + items)
        """
        # Ici tu dois calculer le total pour chaque commande
        # C'est plus complexe car le total n'est pas stocké en base
        # On peut annoter le queryset avec le total calculé
        from django.db.models import F, Sum
        from core_app.models import OrderDishItemModel, OrderDrinkItemModel
        
        # Annotation complexe - à adapter selon ton modèle
        # Pour l'exemple, on suppose que tu as une méthode pour calculer
        return queryset
    
    def filter_max_total(self, queryset, name, value):
        """Filtre par montant total maximum"""
        # Même logique que filter_min_total
        return queryset
    
    def filter_by_dish(self, queryset, name, value):
        """Filtre les commandes contenant un plat spécifique"""
        return queryset.filter(dishes_items__dish__id=value).distinct()
    
    def filter_by_drink(self, queryset, name, value):
        """Filtre les commandes contenant une boisson spécifique"""
        return queryset.filter(drinks_items__drink__id=value).distinct()
    
    def filter_search(self, queryset, name, value):
        """Recherche texte dans les commentaires"""
        return queryset.filter(comment__icontains=value)