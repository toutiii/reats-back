from datetime import timedelta

import django_filters
from core_app.models import OrderModel
from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from utils.enums import OrderStatusEnum


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class OrderFilter(filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")

    created_after = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    created_before = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="lte",
    )

    modified_after = django_filters.DateTimeFilter(field_name="modified", lookup_expr="gte")

    min_total = django_filters.NumberFilter(
        method="filter_min_total",
    )

    max_total = django_filters.NumberFilter(
        method="filter_max_total",
    )

    cooker_id = django_filters.NumberFilter(
        field_name="cooker__id",
    )

    dish_id = django_filters.NumberFilter(
        method="filter_by_dish",
    )

    drink_id = django_filters.NumberFilter(
        method="filter_by_drink",
    )

    scheduled_date_after = django_filters.DateTimeFilter(field_name="scheduled_delivery_date", lookup_expr="gte")

    scheduled_date_before = django_filters.DateTimeFilter(field_name="scheduled_delivery_date", lookup_expr="lte")

    status_in = CharInFilter(
        field_name="status",
        lookup_expr="in",
    )

    search = django_filters.CharFilter(
        method="filter_search",
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("delivery_fees", "delivery_fees"),
            ("scheduled_delivery_date", "scheduled_date"),
        ),
    )

    class Meta:
        model = OrderModel
        fields = {
            "status": ["exact"],
            "created": ["gte", "lte", "gt", "lt"],
            "delivery_fees": ["gte", "lte"],
            "rating": ["gte", "lte"],
        }

    def filter_status(self, queryset, name, value):
        if value not in dict(OrderStatusEnum.choices()):
            return queryset.none()

        return queryset.filter(status=value)

    def filter_min_total(self, queryset, name, value):
        """
        Filtre par montant total minimum
        Le montant total est calculé (delivery_fees + items)
        """
        from django.db.models import F, FloatField, Sum, Value
        from django.db.models.functions import Coalesce

        queryset = queryset.annotate(
            dishes_total=Coalesce(
                Sum(F("dishes_items__dish__price") * F("dishes_items__dish_quantity")),
                Value(0.0, output_field=FloatField()),
            ),
            drinks_total=Coalesce(
                Sum(F("drinks_items__drink__price") * F("drinks_items__drink_quantity")),
                Value(0.0, output_field=FloatField()),
            ),
        ).annotate(
            items_total=F("dishes_total") + F("drinks_total"),
            total_amount=F("items_total") + Coalesce(F("delivery_fees"), Value(0.0, output_field=FloatField())),
        )

        return queryset.filter(total_amount__gte=value)

    def filter_max_total(self, queryset, name, value):
        """Filtre par montant total maximum"""
        return self.filter_min_total(queryset, name, 0).filter(total_amount__lte=value)

    def filter_by_dish(self, queryset, name, value):
        """Filtre les commandes contenant un plat spécifique"""
        return queryset.filter(dishes_items__dish__id=value).distinct()

    def filter_by_drink(self, queryset, name, value):
        """Filtre les commandes contenant une boisson spécifique"""
        return queryset.filter(drinks_items__drink__id=value).distinct()

    def filter_search(self, queryset, name, value):
        """Recherche texte dans les commentaires"""
        return queryset.filter(comment__icontains=value)


class OrderHistoryFilter(filters.FilterSet):
    status = django_filters.CharFilter(
        field_name="status",
        lookup_expr="exact",
    )

    status_in = CharInFilter(
        field_name="status",
        lookup_expr="in",
    )

    created_after = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    created_before = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="lte",
    )

    start_date = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="gte",
    )

    end_date = django_filters.DateTimeFilter(
        field_name="created",
        lookup_expr="lte",
    )

    updated_after = django_filters.DateTimeFilter(
        field_name="modified",
        lookup_expr="gte",
    )

    updated_before = django_filters.DateTimeFilter(
        field_name="modified",
        lookup_expr="lte",
    )

    scheduled_date_after = django_filters.DateTimeFilter(
        field_name="scheduled_delivery_date",
        lookup_expr="gte",
    )

    scheduled_date_before = django_filters.DateTimeFilter(
        field_name="scheduled_delivery_date",
        lookup_expr="lte",
    )

    min_total_amount = django_filters.NumberFilter(method="filter_min_total_amount", label="Montant total minimum")

    max_total_amount = django_filters.NumberFilter(method="filter_max_total_amount", label="Montant total maximum")

    customer_id = django_filters.NumberFilter(field_name="customer__id", label="ID du client")

    cooker_id = django_filters.NumberFilter(field_name="cooker__id", label="ID du cuisinier")

    deliver_id = django_filters.NumberFilter(field_name="delivery_man__id", label="ID du livreur")

    min_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="gte", label="Note minimum")

    max_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="lte", label="Note maximum")

    has_rating = django_filters.BooleanFilter(method="filter_has_rating", label="A une note")

    has_comment = django_filters.BooleanFilter(method="filter_has_comment", label="A un commentaire")

    is_scheduled = django_filters.BooleanFilter(field_name="is_scheduled", label="Commande programmée")

    period = django_filters.CharFilter(method="filter_period", label="Période")

    search = django_filters.CharFilter(method="filter_search", label="Recherche")

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("scheduled_delivery_date", "scheduled_date"),
            ("delivery_fees", "delivery_fees"),
            ("rating", "rating"),
        ),
        field_labels={
            "created": "Date de création",
            "modified": "Date de modification",
            "scheduled_delivery_date": "Date de livraison programmée",
            "delivery_fees": "Frais de livraison",
            "rating": "Note",
        },
    )

    class Meta:
        model = OrderModel
        fields = {
            "status": ["exact", "in"],
            "created": ["gte", "lte", "gt", "lt"],
            "modified": ["gte", "lte"],
            "scheduled_delivery_date": ["gte", "lte"],
            "rating": ["gte", "lte", "exact"],
            "delivery_fees": ["gte", "lte"],
        }

    def filter_min_total_amount(self, queryset, name, value):
        """
        Filtre par montant total minimum
        Montant total = sum(items) + delivery_fees
        """
        from django.db.models import F, FloatField, Sum, Value
        from django.db.models.functions import Coalesce

        queryset = queryset.annotate(
            dishes_total=Coalesce(
                Sum(F("dishes_items__dish__price") * F("dishes_items__dish_quantity")),
                Value(0.0, output_field=FloatField()),
            ),
            drinks_total=Coalesce(
                Sum(F("drinks_items__drink__price") * F("drinks_items__drink_quantity")),
                Value(0.0, output_field=FloatField()),
            ),
        ).annotate(
            items_total=F("dishes_total") + F("drinks_total"),
            total_amount=F("items_total") + Coalesce(F("delivery_fees"), Value(0.0, output_field=FloatField())),
        )

        return queryset.filter(total_amount__gte=value)

    def filter_max_total_amount(self, queryset, name, value):
        """
        Filtre par montant total maximum
        """
        return self.filter_min_total_amount(queryset, name, 0).filter(total_amount__lte=value)

    def filter_has_rating(self, queryset, name, value):
        """
        Filtre les commandes avec/sans note
        """
        if value:
            return queryset.filter(rating__gt=0)
        else:
            return queryset.filter(rating=0)

    def filter_has_comment(self, queryset, name, value):
        """
        Filtre les commandes avec/sans commentaire
        """
        if value:
            return queryset.filter(comment__isnull=False).exclude(comment="")
        else:
            return queryset.filter(Q(comment__isnull=True) | Q(comment=""))

    def filter_period(self, queryset, name, value):
        """
        Filtre par période prédéfinie
        """
        now = timezone.now()

        if value == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date)

        elif value == "yesterday":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date, created__lt=end_date)

        elif value == "last_7_days":
            start_date = now - timedelta(days=7)
            return queryset.filter(created__gte=start_date)

        elif value == "last_30_days":
            start_date = now - timedelta(days=30)
            return queryset.filter(created__gte=start_date)

        elif value == "this_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date)

        elif value == "last_month":
            first_day_of_current_month = now.replace(day=1)
            last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
            first_day_of_last_month = last_day_of_last_month.replace(day=1)

            return queryset.filter(created__gte=first_day_of_last_month, created__lte=last_day_of_last_month)

        elif value == "this_year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date)

        return queryset

    def filter_search(self, queryset, name, value):
        """
        Recherche dans les commentaires, noms des plats/boissons, etc.
        """
        return queryset.filter(
            Q(comment__icontains=value)
            | Q(dishes_items__dish__name__icontains=value)
            | Q(drinks_items__drink__name__icontains=value)
            | Q(customer__firstname__icontains=value)
            | Q(customer__lastname__icontains=value)
            | Q(cooker__firstname__icontains=value)
            | Q(cooker__lastname__icontains=value)
        ).distinct()
