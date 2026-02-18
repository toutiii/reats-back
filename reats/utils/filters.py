from datetime import timedelta

import django_filters
from core_app.models import DishModel, OrderModel
from django.conf import settings
from django.core.validators import RegexValidator
from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from utils.enums import ErrorMessageEnum, OrderStatusEnum


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class OrderFilter(filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")
    status_in = CharInFilter(field_name="status", lookup_expr="in")

    # Dates with 2-year security limit
    created_after = django_filters.DateTimeFilter(method="filter_created_after")
    start_date = django_filters.DateTimeFilter(method="filter_created_after")  # Alias history

    created_before = django_filters.DateTimeFilter(method="filter_created_before")
    end_date = django_filters.DateTimeFilter(method="filter_created_before")  # Alias history

    modified_after = django_filters.DateTimeFilter(field_name="modified", lookup_expr="gte")
    updated_after = django_filters.DateTimeFilter(field_name="modified", lookup_expr="gte")  # Alias history

    modified_before = django_filters.DateTimeFilter(field_name="modified", lookup_expr="lte")
    updated_before = django_filters.DateTimeFilter(field_name="modified", lookup_expr="lte")  # Alias history

    scheduled_date_after = django_filters.DateTimeFilter(field_name="scheduled_delivery_date", lookup_expr="gte")
    scheduled_date_before = django_filters.DateTimeFilter(field_name="scheduled_delivery_date", lookup_expr="lte")

    # Amounts
    min_total = django_filters.NumberFilter(method="filter_min_total")
    min_total_amount = django_filters.NumberFilter(method="filter_min_total")  # Alias history

    max_total = django_filters.NumberFilter(method="filter_max_total")
    max_total_amount = django_filters.NumberFilter(method="filter_max_total")  # Alias history

    # Relations
    cooker_id = django_filters.NumberFilter(field_name="cooker__id")
    customer_id = django_filters.NumberFilter(field_name="customer__id")
    deliver_id = django_filters.NumberFilter(field_name="delivery_man__id")
    dish_id = django_filters.NumberFilter(method="filter_by_dish")
    drink_id = django_filters.NumberFilter(method="filter_by_drink")

    # Ratings
    rating = django_filters.NumberFilter(field_name="rating", lookup_expr="exact")
    min_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="gte")
    max_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="lte")
    has_rating = django_filters.BooleanFilter(method="filter_has_rating")
    has_comment = django_filters.BooleanFilter(method="filter_has_comment")

    is_scheduled = django_filters.BooleanFilter(field_name="is_scheduled")
    period = django_filters.CharFilter(method="filter_period")

    search = django_filters.CharFilter(
        method="filter_search",
        validators=[
            RegexValidator(
                regex=r"^[\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ\'-]+$",
                message=ErrorMessageEnum.SEARCH_INVALID_CHARACTERS,
            )
        ],
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("delivery_fees", "delivery_fees"),
            ("scheduled_delivery_date", "scheduled_date"),
            ("rating", "rating"),
        ),
    )

    class Meta:
        model = OrderModel
        fields = [
            "status",
            "created",
            "modified",
            "delivery_fees",
            "rating",
            "is_scheduled",
        ]

    def clean(self):
        cleaned_data = super().clean()

        # Validation croisée des dates (aliases compris)
        after = cleaned_data.get("created_after") or cleaned_data.get("start_date")
        before = cleaned_data.get("created_before") or cleaned_data.get("end_date")

        if after and before and after > before:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"created_after": ErrorMessageEnum.INVALID_DATE_RANGE})

        return cleaned_data

    def _validate_date_limit(self, value, field_name):
        """Valide que la date ne remonte pas à plus de 2 ans."""
        if not value:
            return value
        limit_date = timezone.now() - timedelta(days=settings.ORDER_HISTORY_LIMIT_DAYS)
        if value < limit_date:
            raise ValidationError(
                {field_name: f"La date ne peut pas remonter à plus de 2 ans (limite: {limit_date.date()})."}
            )
        return value

    def filter_created_after(self, queryset, name, value):
        value = self._validate_date_limit(value, name)
        return queryset.filter(created__gte=value)

    def filter_created_before(self, queryset, name, value):
        # On pourrait aussi limiter dans le futur si besoin, mais ici on reste sur le passé
        return queryset.filter(created__lte=value)

    def filter_status(self, queryset, name, value):
        if value not in dict(OrderStatusEnum.choices()):
            return queryset.none()
        return queryset.filter(status=value)

    def filter_min_total(self, queryset, name, value):
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
        return self.filter_min_total(queryset, name, 0).filter(total_amount__lte=value)

    def filter_by_dish(self, queryset, name, value):
        return queryset.filter(dishes_items__dish__id=value).distinct()

    def filter_by_drink(self, queryset, name, value):
        return queryset.filter(drinks_items__drink__id=value).distinct()

    def filter_has_rating(self, queryset, name, value):
        return queryset.filter(rating__gt=0) if value else queryset.filter(rating=0)

    def filter_has_comment(self, queryset, name, value):
        if value:
            return queryset.filter(comment__isnull=False).exclude(comment="")
        return queryset.filter(Q(comment__isnull=True) | Q(comment=""))

    def filter_period(self, queryset, name, value):
        now = timezone.now()
        if value == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date)
        elif value == "yesterday":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(created__gte=start_date, created__lt=end_date)
        elif value == "last_7_days":
            return queryset.filter(created__gte=now - timedelta(days=7))
        elif value == "last_30_days":
            return queryset.filter(created__gte=now - timedelta(days=30))
        elif value == "this_month":
            return queryset.filter(created__gte=now.replace(day=1, hour=0, minute=0, second=0))
        elif value == "last_month":
            first_day_curr = now.replace(day=1)
            last_day_last = first_day_curr - timedelta(days=1)
            first_day_last = last_day_last.replace(day=1)
            return queryset.filter(created__gte=first_day_last, created__lte=last_day_last)
        elif value == "this_year":
            return queryset.filter(created__gte=now.replace(month=1, day=1, hour=0, minute=0, second=0))
        return queryset

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(comment__icontains=value)
            | Q(dishes_items__dish__name__icontains=value)
            | Q(drinks_items__drink__name__icontains=value)
            | Q(customer__firstname__icontains=value)
            | Q(customer__lastname__icontains=value)
            | Q(cooker__firstname__icontains=value)
            | Q(cooker__lastname__icontains=value)
        ).distinct()


class DishFilter(filters.FilterSet):
    search = django_filters.CharFilter(lookup_expr="icontains", field_name="name")
    available = django_filters.BooleanFilter(field_name="is_enabled")

    class Meta:
        model = DishModel
        fields = ["search", "available"]
