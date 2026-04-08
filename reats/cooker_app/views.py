from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, List, Optional, Tuple, Type, TypedDict, Union

import django_filters
from core_app.models import (
    CookerModel,
    DishImageModel,
    DishModel,
    DrinkImageModel,
    DrinkModel,
    IngredientDishModel,
    IngredientDrinkModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from core_app.serializers import (
    DishDetailSerializer,
    DishListSerializer,
    DrinkDetailSerializer,
    DrinkListSerializer,
    IngredientDishSerializer,
    IngredientDrinkSerializer,
    OrderPATCHSerializer,
)
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, F, OuterRef, Q, QuerySet, Subquery, Sum
from django.utils import timezone
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.views import TokenViewBase
from utils.common import (
    activate_user,
    compute_order_items_total_amount,
    compute_order_total_amount,
    create_stripe_refund,
    delete_s3_object,
    format_phone,
    is_otp_valid,
    send_otp,
    update_cooker_acceptance_rate,
    upload_image_to_s3,
)
from utils.custom_api_reponse import StandardizedResponseMixin
from utils.custom_permissions import CustomAPIKeyPermission, UserPermission
from utils.enums import (
    ErrorCodeEnum,
    ErrorMessageEnum,
    MonthChartLabelEnum,
    OrderStatusEnum,
    SuccessMessageEnum,
    TimeFrameEnum,
    TodayChartLabelEnum,
    WeekChartLabelEnum,
    YearChartLabelEnum,
)
from utils.filters import DishFilter, DrinkFilter
from utils.paginations import StandardizedResultsSetPagination

from .serializers import (
    CookerGETSerializer,
    CookerOrderGETSerializer,
    CookerSerializer,
    DashboardStatsSerializer,
    DishPATCHSerializer,
    DishPOSTSerializer,
    DrinkPATCHSerializer,
    DrinkPOSTSerializer,
    PopularItemSerializer,
    RecentReviewSerializer,
    TokenObtainPairWithoutPasswordSerializer,
    TokenObtainRefreshWithoutPasswordSerializer,
)

logger = logging.getLogger("watchtower-logger")


class DateRangeDict(TypedDict):
    """Type definition for date range dictionary used in dashboard stats."""

    current_period_start: datetime
    current_period_end: datetime
    previous_period_start: datetime
    previous_period_end: datetime


class CookerView(StandardizedResponseMixin, ModelViewSet):
    queryset = CookerModel.objects.all()

    def get_permissions(self) -> list:
        permission_classes: list[Type[BasePermission]] = []
        if self.action in (
            "auth",
            "ask_otp",
            "create",
            "otp_verify",
        ):
            permission_classes.append(CustomAPIKeyPermission)
        else:
            permission_classes.append(UserPermission)

        return [permission() for permission in permission_classes]

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PATCH"):
            self.serializer_class = CookerSerializer

        if self.request.method == "GET":
            self.serializer_class = CookerGETSerializer

        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self.success(response.data)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return self.success(response.data)

    def perform_create(self, serializer: BaseSerializer) -> None:
        super().perform_create(serializer)
        logger.info("Cooker model created, sending OTP...")
        send_otp(serializer.validated_data.get("phone"))

    def create(self, request, *args, **kwargs):
        logger.info(f"Received cooker creation request: {request.data}")
        try:
            response = super().create(request, *args, **kwargs)
            logger.info("Cooker creation successful")
            return self.success(data=response.data, status_code=status.HTTP_201_CREATED)
        except IntegrityError as err:
            logger.error(f"Customer creation failed- duplicate phone number: {err}")
            return self.error(
                message=ErrorMessageEnum.CUSTOMER_ALREADY_EXISTS,
                code=ErrorCodeEnum.USER_ALREADY_EXISTS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs) -> Response:
        kwargs.pop("pk", None)  # Ensure pk is handled smoothly by parent
        response = super().partial_update(request, *args, **kwargs)
        return self.success(data=response.data)

    def update(self, request, *args, **kwargs) -> Response:
        kwargs.pop("pk", None)  # Ensure pk is handled smoothly by parent
        response = super().update(request, *args, **kwargs)
        return self.success(data=response.data)

    @action(detail=True, methods=["patch"], url_path="photo")
    def photo(self, request, pk=None) -> Response:
        cooker: CookerModel = self.get_object()
        old_photo_key: str = cooker.photo

        if "photo" not in self.request.FILES:
            return self.error(
                message="No photo provided",
                code="INVALID_DATA",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        photo = "cookers" + "/" + str(cooker.pk) + "/" + "profile_pics" + "/" + self.request.FILES["photo"].name
        upload_image_to_s3(self.request.FILES["photo"], photo)

        cooker.photo = photo
        cooker.save()

        if old_photo_key and not old_photo_key.endswith("default-profile-pic.jpg"):
            delete_s3_object(old_photo_key)

        return self.success(data={"photo": cooker.photo}, message=SuccessMessageEnum.OPERATION_SUCCESSFUL)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: CookerModel = self.get_object()
        instance.is_deleted = True
        instance.save()
        return self.success(message=SuccessMessageEnum.ACCOUNT_DELETED)

    @action(methods=["post"], detail=False, url_path="otp-verify")
    def otp_verify(self, request) -> Response:
        result = is_otp_valid(request.data)

        if result:
            activate_user(CookerModel, request.data)
            return self.success(message=SuccessMessageEnum.ACCOUNT_ACTIVATED)

        return self.error(
            message=ErrorMessageEnum.INVALID_OTP_CODE,
            code=ErrorCodeEnum.OTP_INVALID,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @action(methods=["post"], detail=False)
    def auth(self, request) -> Response:
        phone = request.data.get("phone")

        if phone is None:
            return self.error(
                ErrorMessageEnum.PHONE_REQUIRED,
                code=ErrorCodeEnum.PHONE_REQUIRED,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return self.error(
                ErrorMessageEnum.PHONE_INVALID_FORMAT,
                code=ErrorCodeEnum.PHONE_INVALID_FORMAT,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cooker: CookerModel = CookerModel.objects.get(phone=e164_phone_format)
        except CookerModel.DoesNotExist:
            return self.error(
                ErrorMessageEnum.USER_NOT_FOUND,
                code=ErrorCodeEnum.USER_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not cooker.is_activated:
            return self.error(
                ErrorMessageEnum.ACCOUNT_NOT_ACTIVATED,
                code=ErrorCodeEnum.ACCOUNT_NOT_ACTIVATED,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        otp_response: Union[dict, None] = send_otp(e164_phone_format)

        if otp_response is None:
            return self.error(
                ErrorMessageEnum.OTP_SEND_FAILED,
                code=ErrorCodeEnum.OTP_SEND_FAILED,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Simplified success check (assuming previous logic was detailed but basic success is mostly what matters)
        # Keeping previous logic structure but wrapping response

        otp_response_status_code = (
            otp_response.get("MessageResponse", {}).get("Result", {}).get(e164_phone_format, {}).get("StatusCode")
        )

        if otp_response_status_code != status.HTTP_200_OK:
            return self.error(
                ErrorMessageEnum.OTP_PROVIDER_ERROR,
                code=ErrorCodeEnum.OTP_PROVIDER_ERROR,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        otp_response_delivery_status = (
            otp_response.get("MessageResponse", {}).get("Result", {}).get(e164_phone_format, {}).get("DeliveryStatus")
        )

        if otp_response_delivery_status != "SUCCESSFUL":
            return self.error(
                ErrorMessageEnum.OTP_DELIVERY_FAILED,
                code=ErrorCodeEnum.OTP_DELIVERY_FAILED,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return self.success(message=SuccessMessageEnum.OTP_SENT)

    @action(methods=["post"], detail=False, url_path="otp/ask")
    def ask_otp(self, request) -> Response:
        phone = request.data.get("phone")

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return self.error(
                message=ErrorMessageEnum.PHONE_INVALID_FORMAT,
                code=ErrorCodeEnum.PHONE_INVALID_FORMAT,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        send_otp(e164_phone_format)

        return self.success(message=SuccessMessageEnum.OTP_SENT_FR)


class DashboardView(StandardizedResponseMixin, GenericViewSet):
    permission_classes = [UserPermission]
    pagination_class = StandardizedResultsSetPagination

    def list(self, request) -> Response:
        start_date_str: Union[str, None] = request.query_params.get("start_date")
        end_date_str: Union[str, None] = request.query_params.get("end_date")

        if start_date_str is None or end_date_str is None:
            return self.error(
                message=ErrorMessageEnum.MISSING_PARAMETERS,
                code=ErrorCodeEnum.MISSING_PARAMETERS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        except ValueError:
            return self.error(
                message=ErrorMessageEnum.INVALID_DATE_FORMAT,
                code=ErrorCodeEnum.INVALID_DATE_FORMAT,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        orders = (
            OrderModel.objects.filter(created__gte=start_date)
            .filter(created__lte=end_date)
            .filter(cooker=request.user.pk)
            .exclude(status__in=[OrderStatusEnum.DRAFT])
            .values("status")  # Group by 'status'
            .annotate(count=Count("id"))  # Count the number of orders for each status
            .values_list("status", "count")  # Return as a list of tuples
        )
        orders_dict = {status: count for status, count in orders}

        return self.success(data=orders_dict)

    @action(methods=["get"], detail=False, url_path="stats")
    def stats(self, request) -> Response:
        period = request.query_params.get("period", TimeFrameEnum.TODAY.value)
        cooker_id = request.user.pk

        date_range = self._get_date_range(period)
        stats = self._calculate_stats(cooker_id, date_range)
        revenue_chart = self._generate_revenue_chart(cooker_id, period, date_range)

        data = {
            "period": period,
            "stats": stats,
            "revenue_chart": revenue_chart,
        }

        serializer = DashboardStatsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return self.success(data=serializer.data)

    @action(methods=["get"], detail=False, url_path="popular-items")
    def popular_items(self, request) -> Response:
        """Return paginated list of popular items for the given period."""
        period = request.query_params.get("period", TimeFrameEnum.TODAY.value)
        cooker_id = request.user.pk

        date_range = self._get_date_range(period)
        queryset = self._get_popular_items_queryset(cooker_id, date_range)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PopularItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PopularItemSerializer(queryset, many=True)
        return self.success(data=serializer.data)

    def _get_date_range(self, period: str) -> DateRangeDict:
        now = timezone.now()

        if period == TimeFrameEnum.TODAY.value:
            current_period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_period_start = current_period_start - timedelta(days=1)
            previous_period_end = current_period_start
        elif period == TimeFrameEnum.WEEK.value:
            current_period_start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            previous_period_start = current_period_start - timedelta(days=7)
            previous_period_end = current_period_start
        elif period == TimeFrameEnum.MONTH.value:
            current_period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_period_end = current_period_start
            previous_period_start = (current_period_start - timedelta(days=1)).replace(day=1)
        elif period == TimeFrameEnum.YEAR.value:
            current_period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            previous_period_end = current_period_start
            previous_period_start = current_period_start.replace(year=current_period_start.year - 1)
        else:
            current_period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            previous_period_start = current_period_start - timedelta(days=1)
            previous_period_end = current_period_start

        return {
            "current_period_start": current_period_start,
            "current_period_end": now,
            "previous_period_start": previous_period_start,
            "previous_period_end": previous_period_end,
        }

    def _get_order_counts(self, cooker_id: int) -> dict[str, int]:
        """Get active and pending order counts for a cooker."""
        counts = OrderModel.objects.filter(cooker_id=cooker_id).aggregate(
            active_count=Count(
                "id",
                filter=Q(
                    status__in=[
                        OrderStatusEnum.PENDING,
                        OrderStatusEnum.PROCESSING,
                        OrderStatusEnum.COMPLETED,
                    ]
                ),
            ),
            pending_count=Count("id", filter=Q(status=OrderStatusEnum.PENDING)),
        )
        return {"active": counts["active_count"], "pending": counts["pending_count"]}

    def _get_revenue_for_orders(self, orders: QuerySet[OrderModel]) -> float:
        """Calculate total revenue from a queryset of orders."""
        delivered_orders = list(orders.filter(status=OrderStatusEnum.DELIVERED))
        return sum(compute_order_total_amount(order) for order in delivered_orders)

    def _get_customers_served(self, orders: QuerySet[OrderModel]) -> int:
        """Get distinct customer count from delivered orders."""
        return orders.filter(status=OrderStatusEnum.DELIVERED).values("customer").distinct().count()

    def _calculate_stats(self, cooker_id: int, date_range: DateRangeDict) -> dict[str, Any]:
        current_orders = OrderModel.objects.filter(
            cooker_id=cooker_id, created__gte=date_range["current_period_start"]
        ).prefetch_related("dishes_items__dish", "drinks_items__drink")

        prev_orders = OrderModel.objects.filter(
            cooker_id=cooker_id,
            created__gte=date_range["previous_period_start"],
            created__lt=date_range["previous_period_end"],
        ).prefetch_related("dishes_items__dish", "drinks_items__drink")

        order_counts = self._get_order_counts(cooker_id)
        current_revenue = self._get_revenue_for_orders(current_orders)
        prev_revenue = self._get_revenue_for_orders(prev_orders)
        current_customers = self._get_customers_served(current_orders)
        prev_customers = self._get_customers_served(prev_orders)

        return {
            "active_orders": {"count": order_counts["active"], "trend": None},
            "pending_orders": {"count": order_counts["pending"], "trend": None},
            "revenue": {
                "amount": current_revenue,
                "currency": settings.DEFAULT_CURRENCY,
                "trend": self._calculate_trend(current_revenue, prev_revenue),
            },
            "customers_served": {
                "count": current_customers,
                "trend": self._calculate_trend(current_customers, prev_customers),
            },
        }

    def _generate_revenue_chart(self, cooker_id: int, period: str, date_range: DateRangeDict) -> dict[str, List[Any]]:
        orders = list(
            OrderModel.objects.filter(
                cooker_id=cooker_id,
                created__gte=date_range["current_period_start"],
                status=OrderStatusEnum.DELIVERED,
            )
            .prefetch_related("dishes_items__dish", "drinks_items__drink")
            .order_by("created")
        )

        def _aggregate_by_time_slot(
            chart_labels: List[str],
            time_slot_index_for_order: Callable[[Any], Optional[int]],
        ) -> Tuple[List[str], List[float]]:
            """
            Aggregate order totals into time slots (one slot per label).
            """
            slot_totals: List[float] = [0.0] * len(chart_labels)

            for order in orders:
                time_slot_index = time_slot_index_for_order(order)
                if time_slot_index is None:
                    continue
                slot_totals[time_slot_index] += float(compute_order_total_amount(order))

            return chart_labels, slot_totals

        match period:
            case TimeFrameEnum.TODAY.value:
                labels = [label.value for label in TodayChartLabelEnum]

                def time_slot_index_for_order(order: Any) -> Optional[int]:
                    # 0..23 -> 0..5 (4-hour slots)
                    return order.created.hour // 4

            case TimeFrameEnum.WEEK.value:
                labels = [label.value for label in WeekChartLabelEnum]

                def time_slot_index_for_order(order: Any) -> Optional[int]:
                    # Python weekday: 0=Monday, 6=Sunday
                    return order.created.weekday()

            case TimeFrameEnum.MONTH.value:
                labels = [label.value for label in MonthChartLabelEnum]
                start_date = date_range["current_period_start"]

                def time_slot_index_for_order(order: Any) -> Optional[int]:
                    # Keep original behavior: only count orders within the first 4 weeks
                    days_since_start = (order.created - start_date).days
                    week_index = days_since_start // 7
                    return week_index if 0 <= week_index < 4 else None

            case TimeFrameEnum.YEAR.value:
                labels = [label.value for label in YearChartLabelEnum]

                def time_slot_index_for_order(order: Any) -> Optional[int]:
                    # 1..12 -> 0..11
                    return order.created.month - 1

            case _:
                # Default to 'today' behavior for invalid periods
                labels = [label.value for label in TodayChartLabelEnum]

                def time_slot_index_for_order(order: Any) -> Optional[int]:
                    return order.created.hour // 4

        labels, data = _aggregate_by_time_slot(labels, time_slot_index_for_order)
        return {"labels": labels, "data": data}

    @action(methods=["get"], detail=False, url_path="recent-reviews")
    def recent_reviews(self, request) -> Response:
        """Return paginated list of recent reviews."""
        cooker_id = request.user.pk
        queryset = self._get_recent_reviews_queryset(cooker_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = RecentReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecentReviewSerializer(queryset, many=True)
        return self.success(data=serializer.data)

    def _get_recent_reviews_queryset(self, cooker_id: int) -> QuerySet:
        """Return QuerySet of recent reviews (orders with ratings/comments)."""
        return (
            OrderModel.objects.filter(cooker_id=cooker_id, rating__gt=0)
            .exclude(comment__isnull=True)
            .exclude(comment="")
            .select_related("customer")
            .order_by("-modified")
        )

    def _get_popular_items_queryset(self, cooker_id: int, date_range: DateRangeDict) -> QuerySet:
        """Return combined QuerySet of popular dishes and drinks using union."""
        # Get popular dishes with normalized field names
        primary_image_subq = DishImageModel.objects.filter(dish=OuterRef("dish"), is_primary=True).values("key")[:1]

        dishes = (
            OrderDishItemModel.objects.filter(
                order__cooker_id=cooker_id,
                order__created__gte=date_range["current_period_start"],
                order__status=OrderStatusEnum.DELIVERED,
            )
            .annotate(primary_image_key=Subquery(primary_image_subq))
            .values(
                item_id=F("dish__id"),
                item_name=F("dish__name"),
                item_photo=F("primary_image_key"),
                item_price=F("dish__price"),
            )
            .annotate(total_sold=Sum("dish_quantity"))
        )

        # Get popular drinks with normalized field names
        primary_drink_image_subq = DrinkImageModel.objects.filter(drink=OuterRef("drink"), is_primary=True).values(
            "key"
        )[:1]

        drinks = (
            OrderDrinkItemModel.objects.filter(
                order__cooker_id=cooker_id,
                order__created__gte=date_range["current_period_start"],
                order__status=OrderStatusEnum.DELIVERED,
            )
            .annotate(primary_image_key=Subquery(primary_drink_image_subq))
            .values(
                item_id=F("drink__id"),
                item_name=F("drink__name"),
                item_photo=F("primary_image_key"),
                item_price=F("drink__price"),
            )
            .annotate(total_sold=Sum("drink_quantity"))
        )

        # Combine using union and order by total_sold
        # Note: union() requires identical field names and types
        return dishes.union(drinks).order_by("-total_sold")

    def _calculate_trend(self, current: float, previous: float) -> Union[str, None]:
        if not previous:
            return None
        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.0f}%"


class IngredientsEndpointMixin:
    """
    Mixin to provide the GET /{items}/ingredients/ endpoint with custom structure.
    Requires the viewset to define `ingredient_model` and `ingredient_serializer_class`
    and inherit from `StandardizedResponseMixin`.
    """

    ingredient_model: Any = None
    ingredient_serializer_class: Any = None

    @action(detail=False, methods=["get"], url_path="ingredients")
    def ingredients(self, request, *args, **kwargs) -> Response:
        queryset = self.ingredient_model.objects.all().order_by("name")
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))

        category_counts = (
            self.ingredient_model.objects.filter(id__in=queryset.values_list("id", flat=True))
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        categories_data = [
            {
                "id": str(item["category"]),
                "name": str(item["category"]).capitalize() if item["category"] else "Autre",
                "count": item["count"],
            }
            for item in category_counts
            if item["category"]
        ]

        serializer = self.ingredient_serializer_class(queryset, many=True)

        response_data = {
            "ingredients": serializer.data,
            "categories": categories_data,
        }

        return self.success(data=response_data)  # type: ignore


class DishView(StandardizedResponseMixin, IngredientsEndpointMixin, ModelViewSet):
    queryset = DishModel.objects.filter(is_deleted=False).all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = DishFilter
    pagination_class = StandardizedResultsSetPagination

    ingredient_model = IngredientDishModel
    ingredient_serializer_class = IngredientDishSerializer

    def _annotated_queryset(self):
        return self.queryset.prefetch_related("ingredients", "images").annotate(
            current_orders=Count(
                "orderdishitemmodel",
                filter=Q(
                    orderdishitemmodel__order__status__in=[
                        OrderStatusEnum.PROCESSING,
                        OrderStatusEnum.IN_DELIVERY,
                    ]
                ),
                distinct=True,
            )
        )

    def get_queryset(self):
        if self.action in ("retrieve", "update", "partial_update", "destroy", "toggle_availability"):
            return self._annotated_queryset().filter(cooker__id=self.request.user.pk)

        qs = self._annotated_queryset()
        if self.action == "list":
            qs = qs.filter(cooker__id=self.request.user.pk)
            if "is_enabled" not in self.request.query_params:
                qs = qs.filter(is_enabled=True)
        return qs

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "toggle_availability":
            return DishListSerializer
        if self.request.method in ("POST", "PUT"):
            return DishPOSTSerializer
        if self.request.method == "PATCH":
            return DishPATCHSerializer
        if self.action == "retrieve":
            return DishDetailSerializer
        return DishListSerializer

    def _build_s3_key(self, cooker_pk: int, category: str, filename: str) -> str:
        return f"cookers/{cooker_pk}/dishes/{category}/{filename}"

    def perform_create(self, serializer: BaseSerializer) -> None:
        cooker_pk = serializer.validated_data["cooker"].pk
        category = serializer.validated_data["category"]
        photos = self.request.FILES.getlist("photos") or (
            [self.request.FILES["photo"]] if "photo" in self.request.FILES else []
        )

        dish = serializer.save()

        for idx, photo_file in enumerate(photos):
            s3_key = self._build_s3_key(cooker_pk, category, photo_file.name)
            upload_image_to_s3(photo_file, s3_key)
            DishImageModel.objects.create(
                dish=dish,
                key=s3_key,
                is_primary=(idx == 0),
                position=idx,
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid data",
                code="INVALID_DATA",
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return self.success(data=serializer.data, status_code=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer: BaseSerializer) -> None:
        current_object = self.get_object()
        cooker_pk = current_object.cooker_id
        category = serializer.validated_data.get("category", current_object.category)
        photos = self.request.FILES.getlist("photos") or (
            [self.request.FILES["photo"]] if "photo" in self.request.FILES else []
        )

        if photos:
            # Replace all existing images with the newly uploaded ones
            for old_image in current_object.images.all():
                if old_image.key and not old_image.key.endswith("default-dish.jpg"):
                    delete_s3_object(old_image.key)
            current_object.images.all().delete()

        dish = serializer.save()

        for idx, photo_file in enumerate(photos):
            s3_key = self._build_s3_key(cooker_pk, category, photo_file.name)
            upload_image_to_s3(photo_file, s3_key)
            DishImageModel.objects.create(
                dish=dish,
                key=s3_key,
                is_primary=(idx == 0),
                position=idx,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return self.success(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    def list(self, request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())

        if not request.query_params.get("search"):
            queryset = queryset.order_by("name")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success(data=serializer.data)

    @action(detail=True, methods=["patch"], url_path="availability")
    def toggle_availability(self, request, *args, **kwargs) -> Response:
        instance: DishModel = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(update_fields=["is_enabled", "modified"])
        instance = self.queryset.get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: DishModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return self.success(message=SuccessMessageEnum.DISH_DELETED)


class DrinkView(StandardizedResponseMixin, IngredientsEndpointMixin, ModelViewSet):
    queryset = DrinkModel.objects.filter(is_deleted=False).all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = DrinkFilter
    pagination_class = StandardizedResultsSetPagination
    ingredient_model = IngredientDrinkModel
    ingredient_serializer_class = IngredientDrinkSerializer

    def _annotated_queryset(self):
        return self.queryset.prefetch_related("images")

    def get_queryset(self):
        if self.action in ("retrieve", "update", "partial_update", "destroy"):
            return self._annotated_queryset().filter(cooker__id=self.request.user.pk)

        qs = self._annotated_queryset()
        if self.action == "list":
            qs = qs.filter(cooker__id=self.request.user.pk)
            if "is_enabled" not in self.request.query_params:
                qs = qs.filter(is_enabled=True)
        return qs

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "toggle_availability":
            return DrinkListSerializer

        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DrinkPOSTSerializer

        if self.request.method == "PATCH":
            self.serializer_class = DrinkPATCHSerializer

        if self.request.method == "GET":
            if self.action == "retrieve":
                self.serializer_class = DrinkDetailSerializer
            else:
                self.serializer_class = DrinkListSerializer

        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error(
                message="Invalid data",
                code="INVALID_DATA",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return self.success(data=serializer.data, status_code=status.HTTP_201_CREATED, headers=headers)

    def _build_s3_key(self, cooker_pk: int | str, filename: str) -> str:
        return f"cookers/{cooker_pk}/drinks/{filename}"

    def perform_create(self, serializer: BaseSerializer) -> None:
        cooker_pk = str(serializer.validated_data["cooker"].pk)
        photos = self.request.FILES.getlist("photos")

        drink = serializer.save()

        for idx, photo_file in enumerate(photos):
            s3_key = self._build_s3_key(cooker_pk, photo_file.name)
            upload_image_to_s3(photo_file, s3_key)
            DrinkImageModel.objects.create(
                drink=drink,
                key=s3_key,
                is_primary=(idx == 0),
                position=idx,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return self.success(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer: BaseSerializer) -> None:
        current_object = self.get_object()
        cooker_pk = str(current_object.cooker.pk)
        photos = self.request.FILES.getlist("photos")

        if photos:
            # Replace all existing images with the newly uploaded ones
            for old_image in current_object.images.all():
                if old_image.key and "default" not in old_image.key:  # type: ignore
                    delete_s3_object(old_image.key)  # type: ignore
            current_object.images.all().delete()  # type: ignore

        drink = serializer.save()

        for idx, photo_file in enumerate(photos):
            s3_key = self._build_s3_key(cooker_pk, photo_file.name)
            upload_image_to_s3(photo_file, s3_key)
            DrinkImageModel.objects.create(
                drink=drink,
                key=s3_key,
                is_primary=(idx == 0),
                position=idx,
            )
        cooker_pk = str(current_object.cooker.pk)
        photos = self.request.FILES.getlist("photos[]")

        if photos:
            # Replace all existing images with the newly uploaded ones
            for old_image in current_object.images.all():
                if old_image.key and "default" not in old_image.key:  # type: ignore
                    delete_s3_object(old_image.key)  # type: ignore
            current_object.images.all().delete()  # type: ignore

        drink = serializer.save()

        for idx, photo_file in enumerate(photos):
            s3_key = self._build_s3_key(cooker_pk, photo_file.name)
            upload_image_to_s3(photo_file, s3_key)
            DrinkImageModel.objects.create(
                drink=drink,
                key=s3_key,
                is_primary=(idx == 0),
                position=idx,
            )

    @action(detail=True, methods=["patch"], url_path="availability")
    def toggle_availability(self, request, *args, **kwargs) -> Response:
        instance: DrinkModel = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(update_fields=["is_enabled", "modified"])
        instance = self.queryset.get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: DrinkModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return self.success(
            message=SuccessMessageEnum.DRINK_DELETED,
        )


class TokenObtainPairWithoutPasswordView(StandardizedResponseMixin, TokenViewBase):
    serializer_class = TokenObtainPairWithoutPasswordSerializer
    permission_classes = [CustomAPIKeyPermission]
    renderer_classes = [JSONRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            raise

        validated_data = serializer.validated_data
        if isinstance(validated_data, dict) and validated_data.get("status") == status.HTTP_400_BAD_REQUEST:
            return self.error(
                ErrorMessageEnum.INVALID_USER,
                code=ErrorCodeEnum.USER_NOT_FOUND,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return self.success(data=validated_data, message=SuccessMessageEnum.TOKEN_GENERATED)


class TokenObtainRefreshWithoutPasswordView(StandardizedResponseMixin, TokenViewBase):
    serializer_class = TokenObtainRefreshWithoutPasswordSerializer
    renderer_classes = [JSONRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            raise

        return self.success(data=serializer.validated_data, message=SuccessMessageEnum.TOKEN_REFRESHED)


class CookerOrderView(
    StandardizedResponseMixin,
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all()

    def partial_update(self, request, *args, **kwargs):
        instance: OrderModel = self.get_object()
        new_status = request.data.get("status")

        if new_status == OrderStatusEnum.PENDING:
            error_message = f"Cookers orders are not supposed to be in the {OrderStatusEnum.PENDING.value} state"
            logger.error(error_message)
            return self.error(
                message=error_message,
                code=ErrorCodeEnum.INVALID_ORDER_STATUS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if new_status:
            try:
                instance.transition_to(new_status)
            except ValueError as e:
                logger.error(e)
                return self.error(
                    message=str(e),
                    code=ErrorCodeEnum.TRANSITION_ERROR,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                logger.error(e)
                return self.error(
                    message=ErrorMessageEnum.INTERNAL_SERVER_ERROR,
                    code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if new_status == OrderStatusEnum.CANCELLED_BY_COOKER:
            amount_to_refund_in_cents = Decimal(
                str(compute_order_items_total_amount(instance) + instance.delivery_fees)
            ) * Decimal("100")
            create_stripe_refund(int(amount_to_refund_in_cents), instance.stripe_payment_intent_id)

        update_cooker_acceptance_rate(instance, new_status)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return self.success(serializer.data)

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method == "GET":
            self.serializer_class = CookerOrderGETSerializer

        elif self.request.method == "PATCH":
            self.serializer_class = OrderPATCHSerializer

        return super().get_serializer_class()

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(cooker__id=request.user.pk)
        request_status: Union[str, None] = self.request.query_params.get("status")

        if request_status is None or request_status not in [
            OrderStatusEnum.PENDING,
            OrderStatusEnum.PROCESSING,
            OrderStatusEnum.COMPLETED,
        ]:
            if request_status is not None:
                logger.error(f"Invalid status {request_status}")
            self.queryset = OrderModel.objects.none()

        if request_status is not None:
            self.queryset = self.queryset.filter(status=request_status).order_by("-modified")

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success(serializer.data)


class CookerOrderHistoryView(StandardizedResponseMixin, ListModelMixin, GenericViewSet):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all().filter(
        status__in=[
            OrderStatusEnum.DELIVERED,
            OrderStatusEnum.CANCELLED_BY_CUSTOMER,
            OrderStatusEnum.CANCELLED_BY_COOKER,
        ]
    )

    serializer_class = CookerOrderGETSerializer

    def list(self, request, *args, **kwargs) -> Response:
        order_status: Union[str, None] = self.request.query_params.get("status")
        start_date: Union[str, None] = self.request.query_params.get("start_date")
        end_date: Union[str, None] = self.request.query_params.get("end_date")
        self.queryset = self.queryset.filter(cooker__id=request.user.pk).order_by("-modified")

        if start_date and end_date:
            start_date_object = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_date_object = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if start_date_object > end_date_object:
                return Response(
                    {
                        "ok": False,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "error": "Start date cannot be greater than end date",
                    }
                )
            self.queryset = self.queryset.filter(
                created__gte=start_date_object,
                created__lte=end_date_object,
            )
        if order_status:
            self.queryset = self.queryset.filter(status=order_status)

        page = self.paginate_queryset(self.queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(self.queryset, many=True)
        return self.success(serializer.data, status_code=status.HTTP_200_OK)
