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
)
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, F, OuterRef, Q, QuerySet, Subquery, Sum
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase
from utils.common import (
    activate_user,
    cancel_payment_intent,
    capture_payment_intent,
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
from utils.custom_permissions import CustomAPIKeyPermission, IsCookerOwner, UserPermission
from utils.enums import (
    CancelledByEnum,
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
    CookerOrderHistorySerializer,
    CookerOrderListSerializer,
    CookerPATCHSerializer,
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
    queryset = CookerModel.objects.filter(is_deleted=False)

    def get_queryset(self):
        # For PATCH/PUT: expose all active cookers so that a missing ID gives 404 and
        # a valid ID belonging to another cooker gives 403 (via IsCookerOwner).
        if self.action in ("partial_update", "update", "photo"):
            return CookerModel.objects.filter(is_deleted=False)
        if self.request.user and self.request.user.is_authenticated:
            return CookerModel.objects.filter(pk=self.request.user.pk, is_deleted=False)
        return super().get_queryset()

    def get_permissions(self) -> List[BasePermission]:
        permission_classes: list[Type[BasePermission]] = []
        if self.action in (
            "auth",
            "ask_otp",
            "create",
            "otp_verify",
        ):
            permission_classes.append(CustomAPIKeyPermission)
        elif self.action in ("partial_update", "update", "photo"):
            permission_classes.append(UserPermission)
            permission_classes.append(IsCookerOwner)
        else:
            permission_classes.append(UserPermission)

        return [permission() for permission in permission_classes]

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method == "POST":
            self.serializer_class = CookerSerializer

        if self.request.method in ("PATCH", "PUT"):
            self.serializer_class = CookerPATCHSerializer

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

    @extend_schema(request=CookerPATCHSerializer, responses={200: CookerGETSerializer})
    def partial_update(self, request, *args, **kwargs) -> Response:
        kwargs.pop("pk", None)
        response = super().partial_update(request, *args, **kwargs)

        updated_cooker = self.get_object()
        logger.info(f"[PATCH] Cooker {updated_cooker.pk} updated in memory. Lastname: {updated_cooker.lastname}")
        return self.success(data=response.data)

    @extend_schema(request=CookerPATCHSerializer, responses={200: CookerGETSerializer})
    def update(self, request, *args, **kwargs) -> Response:
        kwargs.pop("pk", None)
        response = super().update(request, *args, **kwargs)

        updated_cooker = self.get_object()
        logger.info(f"[PUT] Cooker {updated_cooker.pk} updated in memory. Lastname: {updated_cooker.lastname}")
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

    @extend_schema(
        responses={200: OpenApiResponse(description="Cooker account successfully soft-deleted")},
        description="Soft deletes the cooker account.",
    )
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

        try:
            CookerModel.objects.get(phone=e164_phone_format)
        except CookerModel.DoesNotExist:
            logger.error(f"Cooker with phone {e164_phone_format} does not exist.")
            return self.error(
                message=ErrorMessageEnum.USER_NOT_FOUND,
                code=ErrorCodeEnum.USER_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
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
                        OrderStatusEnum.ACCEPTED,
                        OrderStatusEnum.COMPLETED,
                    ]
                ),
            ),
            pending_count=Count("id", filter=Q(status=OrderStatusEnum.PENDING)),
        )
        return {"active": counts["active_count"], "pending": counts["pending_count"]}

    def _get_revenue_for_orders(self, orders: QuerySet[OrderModel]) -> float:
        """Calculate total revenue from a queryset of orders."""
        delivered_orders = list(orders.filter(status=OrderStatusEnum.COMPLETED))
        return sum(compute_order_total_amount(order) for order in delivered_orders)

    def _get_customers_served(self, orders: QuerySet[OrderModel]) -> int:
        """Get distinct customer count from delivered orders."""
        return orders.filter(status=OrderStatusEnum.COMPLETED).values("customer").distinct().count()

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
                status=OrderStatusEnum.COMPLETED,
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
                order__status=OrderStatusEnum.COMPLETED,
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
                order__status=OrderStatusEnum.COMPLETED,
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

    @extend_schema(
        summary="List available ingredients",
        description=(
            "Returns all available ingredients grouped by category, with category counts.\n\n"
            "This endpoint is available on both `/dishes/ingredients/` and `/drinks/ingredients/`.\n\n"
            "**Query parameters:**\n"
            "- `search` (string, optional): Filter ingredients by name or code (case-insensitive)."
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter ingredients by name or code (case-insensitive partial match)",
                required=False,
                examples=[OpenApiExample(name="Search for ginger", value="ginger")],
            ),
        ],
        responses={200: OpenApiResponse(description="Ingredient list with category counts")},
        examples=[
            OpenApiExample(
                name="Ingredient list response",
                value={
                    "success": True,
                    "data": {
                        "ingredients": [
                            {
                                "id": 1,
                                "code": "crayfish",
                                "name": "Crayfish",
                                "category": "seafood",
                                "is_allergen": True,
                            },
                            {
                                "id": 2,
                                "code": "eru_leaves",
                                "name": "Eru leaves",
                                "category": "vegetable",
                                "is_allergen": False,
                            },
                            {"id": 3, "code": "ginger", "name": "Ginger", "category": "spice", "is_allergen": False},
                            {"id": 4, "code": "palm_oil", "name": "Palm oil", "category": "oil", "is_allergen": False},
                        ],
                        "categories": [
                            {"id": "vegetable", "name": "Vegetable", "count": 5},
                            {"id": "spice", "name": "Spice", "count": 3},
                            {"id": "seafood", "name": "Seafood", "count": 2},
                            {"id": "oil", "name": "Oil", "count": 1},
                        ],
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
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
    """
    Dish management for the authenticated restaurant (cooker).

    Provides CRUD operations, availability toggling, and ingredient listing
    for dishes belonging to the authenticated cooker.
    """

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
                        OrderStatusEnum.ACCEPTED,
                        OrderStatusEnum.DELIVERING,
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

    @extend_schema(
        summary="Create a dish",
        description=(
            "Creates a new dish for the authenticated restaurant.\n\n"
            "This endpoint accepts **multipart/form-data** to allow photo uploads alongside JSON fields.\n\n"
            "**Fields:**\n"
            "- `photos` (file[], required): One or more dish images. The first image becomes the primary image.\n"
            "- `cooker` (int, required): The cooker ID.\n"
            "- `name` (string, required): Dish name.\n"
            "- `price` (float, required): Selling price.\n"
            "- `category` (string, required): One of `dish`, `starter`, `dessert`.\n"
            "- `country` (string, required): Country of origin.\n"
            "- `description` (string, optional): Dish description.\n"
            "- `cost` (float, optional): Cost price for margin calculation.\n"
            "- `preparation_time` (int, optional): Preparation time in minutes.\n"
            "- `max_concurrent_orders` (int, optional): Max simultaneous orders (default: 10).\n"
            "- `ingredients` (JSON array, optional): Array of `{code, name, category?, is_allergen?}` objects.\n"
            "- `nutritional_info` (JSON object, optional): `{calories, proteins, carbohydrates, fats, fiber}`."
        ),
        request={
            "multipart/form-data": DishPOSTSerializer,
        },
        responses={
            201: OpenApiResponse(response=DishPOSTSerializer, description="Dish created successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                name="Create an Eru dish",
                description="Example: creating a Cameroonian dish with ingredients, nutritional info and photos.",
                value={
                    "cooker": 6,
                    "name": "Eru",
                    "description": "Traditional Cameroonian dish with meat and skin",
                    "price": 10.99,
                    "cost": 5.50,
                    "category": "dish",
                    "country": "cameroun",
                    "preparation_time": 45,
                    "max_concurrent_orders": 10,
                    "photos": ["(binary file)"],
                    "ingredients": [
                        {"code": "eru_leaves", "name": "Eru leaves", "category": "vegetable", "is_allergen": False},
                        {"code": "waterleaf", "name": "Waterleaf", "category": "vegetable", "is_allergen": False},
                        {"code": "palm_oil", "name": "Palm oil", "category": "oil", "is_allergen": False},
                        {"code": "crayfish", "name": "Crayfish", "category": "seafood", "is_allergen": True},
                    ],
                    "nutritional_info": {
                        "calories": 350,
                        "proteins": 18.5,
                        "carbohydrates": 12.0,
                        "fats": 22.0,
                        "fiber": 5.0,
                    },
                },
                request_only=True,
                media_type="multipart/form-data",
            ),
            OpenApiExample(
                name="Response — Dish created",
                description="Successful creation response.",
                value={
                    "success": True,
                    "data": {
                        "id": 18,
                        "cooker": 6,
                        "name": "Eru",
                        "description": "Traditional Cameroonian dish with meat and skin",
                        "price": 10.99,
                        "cost": 5.50,
                        "category": "dish",
                        "country": "cameroun",
                        "preparation_time": 45,
                        "max_concurrent_orders": 10,
                        "ingredients": [
                            {
                                "id": 1,
                                "code": "eru_leaves",
                                "name": "Eru leaves",
                                "category": "vegetable",
                                "is_allergen": False,
                            },
                            {
                                "id": 2,
                                "code": "crayfish",
                                "name": "Crayfish",
                                "category": "seafood",
                                "is_allergen": True,
                            },
                        ],
                        "nutritional_info": {
                            "calories": 350,
                            "proteins": 18.5,
                            "carbohydrates": 12.0,
                            "fats": 22.0,
                            "fiber": 5.0,
                        },
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
        tags=["Dishes"],
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

    @extend_schema(
        summary="Full update a dish",
        description=(
            "Fully updates an existing dish. All required fields must be provided.\n\n"
            "Accepts **multipart/form-data**. Sending `photos` replaces all existing images."
        ),
        request={"multipart/form-data": DishPOSTSerializer},
        responses={200: OpenApiResponse(response=DishPOSTSerializer, description="Dish updated")},
        tags=["Dishes"],
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

    @extend_schema(
        summary="Partially update a dish",
        description=(
            "Partially updates an existing dish. Only the provided fields are modified.\n\n"
            "Accepts **multipart/form-data**. Sending `photos` replaces all existing images."
        ),
        request={"multipart/form-data": DishPATCHSerializer},
        responses={200: OpenApiResponse(response=DishPATCHSerializer, description="Dish partially updated")},
        examples=[
            OpenApiExample(
                name="Update price and description",
                value={
                    "price": 12.99,
                    "description": "Updated dish description with more details",
                },
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                name="Replace photos and ingredients",
                value={
                    "photos": ["(binary file)", "(binary file)"],
                    "ingredients": [
                        {"code": "eru_leaves", "name": "Eru leaves", "category": "vegetable", "is_allergen": False},
                        {"code": "palm_oil", "name": "Palm oil", "category": "oil", "is_allergen": False},
                    ],
                },
                request_only=True,
                media_type="multipart/form-data",
            ),
            OpenApiExample(
                name="Response — Dish updated",
                value={
                    "success": True,
                    "data": {
                        "name": "Eru",
                        "price": 12.99,
                        "description": "Updated dish description with more details",
                        "ingredients": [
                            {
                                "id": 1,
                                "code": "eru_leaves",
                                "name": "Eru leaves",
                                "category": "vegetable",
                                "is_allergen": False,
                            },
                            {"id": 3, "code": "palm_oil", "name": "Palm oil", "category": "oil", "is_allergen": False},
                        ],
                        "nutritional_info": {},
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Dishes"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Get dish details",
        description=(
            "Returns the full details of a dish, including all images, "
            "detailed ingredients, and nutritional information."
        ),
        responses={
            200: OpenApiResponse(response=DishDetailSerializer, description="Dish details"),
            404: OpenApiResponse(description="Dish not found"),
        },
        examples=[
            OpenApiExample(
                name="Dish detail — Eru",
                value={
                    "success": True,
                    "data": {
                        "id": 18,
                        "name": "Eru",
                        "description": "Traditional Cameroonian dish with meat and skin",
                        "price": 10.99,
                        "cost": 5.50,
                        "margin": 49.95,
                        "category": "dish",
                        "available": True,
                        "is_enabled": True,
                        "preparation_time": 45,
                        "max_concurrent_orders": 10,
                        "current_orders": 2,
                        "created_at": "2024-05-08T10:00:00Z",
                        "updated_at": "2024-05-08T10:00:00Z",
                        "images": [
                            {
                                "id": 1,
                                "url": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/dishes/dish/eru.png?X-Amz-...",
                                "is_primary": True,
                                "position": 0,
                            },
                            {
                                "id": 2,
                                "url": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/dishes/dish/eru-2.png?X-Amz-...",
                                "is_primary": False,
                                "position": 1,
                            },
                        ],
                        "ingredients": [
                            {
                                "id": 1,
                                "code": "eru_leaves",
                                "name": "Eru leaves",
                                "category": "vegetable",
                                "is_allergen": False,
                            },
                            {
                                "id": 2,
                                "code": "crayfish",
                                "name": "Crayfish",
                                "category": "seafood",
                                "is_allergen": True,
                            },
                        ],
                        "nutritional_info": {
                            "calories": 350,
                            "proteins": 18.5,
                            "carbohydrates": 12.0,
                            "fats": 22.0,
                            "fiber": 5.0,
                        },
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Dishes"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    @extend_schema(
        summary="List dishes",
        description=(
            "Returns a paginated list of dishes for the authenticated restaurant.\n\n"
            "By default, only enabled dishes are returned. Use `is_enabled=false` to include disabled dishes.\n\n"
            "**Available filters:**\n"
            "- `search`: trigram text search on name and description\n"
            "- `is_enabled`: filter by availability (`true`/`false`)\n"
            "- `category`: filter by category (`dish`, `starter`, `dessert`). Comma-separated for multiple values."
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Text search on dish name and description (trigram similarity)",
                required=False,
                examples=[OpenApiExample(name="Search for Eru", value="Eru")],
            ),
            OpenApiParameter(
                name="is_enabled",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by availability. Only enabled dishes are returned by default.",
                required=False,
            ),
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by category. Possible values: `dish`, `starter`, `dessert`. Comma-separated.",
                required=False,
                examples=[
                    OpenApiExample(name="Dishes only", value="dish"),
                    OpenApiExample(name="Dishes and desserts", value="dish,dessert"),
                ],
            ),
        ],
        responses={
            200: OpenApiResponse(response=DishListSerializer(many=True), description="Paginated dish list"),
        },
        examples=[
            OpenApiExample(
                name="Dish list response",
                value={
                    "success": True,
                    "data": {
                        "count": 2,
                        "next": None,
                        "previous": None,
                        "results": [
                            {
                                "id": 16,
                                "name": "Achu",
                                "description": "Traditional dish from West Cameroon",
                                "price": 8.99,
                                "cost": 4.00,
                                "margin": 55.51,
                                "category": "dish",
                                "available": True,
                                "is_enabled": True,
                                "preparation_time": 60,
                                "max_concurrent_orders": 10,
                                "current_orders": 0,
                                "created_at": "2024-05-01T12:00:00Z",
                                "updated_at": "2024-05-01T12:00:00Z",
                                "image": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/dishes/dish/achu.png?X-Amz-...",
                                "ingredients": ["taro", "palm_oil", "limestone"],
                                "nutritional_info": {},
                            },
                            {
                                "id": 18,
                                "name": "Eru",
                                "description": "Traditional Cameroonian dish with meat and skin",
                                "price": 10.99,
                                "cost": 5.50,
                                "margin": 49.95,
                                "category": "dish",
                                "available": True,
                                "is_enabled": True,
                                "preparation_time": 45,
                                "max_concurrent_orders": 10,
                                "current_orders": 1,
                                "created_at": "2024-05-08T10:00:00Z",
                                "updated_at": "2024-05-08T10:00:00Z",
                                "image": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/dishes/dish/eru.png?X-Amz-...",
                                "ingredients": ["eru_leaves", "waterleaf", "crayfish", "palm_oil"],
                                "nutritional_info": {
                                    "calories": 350,
                                    "proteins": 18.5,
                                    "carbohydrates": 12.0,
                                    "fats": 22.0,
                                    "fiber": 5.0,
                                },
                            },
                        ],
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Dishes"],
    )
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

    @extend_schema(
        summary="Toggle dish availability",
        description=(
            "Toggles the `is_enabled` flag of a dish. "
            "If the dish is currently enabled, it becomes disabled and vice-versa.\n\n"
            "No request body is required."
        ),
        request=None,
        responses={200: OpenApiResponse(response=DishListSerializer, description="Dish with updated availability")},
        examples=[
            OpenApiExample(
                name="Dish disabled",
                value={
                    "success": True,
                    "data": {
                        "id": 18,
                        "name": "Eru",
                        "available": False,
                        "is_enabled": False,
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Dishes"],
    )
    @action(detail=True, methods=["patch"], url_path="availability")
    def toggle_availability(self, request, *args, **kwargs) -> Response:
        instance: DishModel = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(update_fields=["is_enabled"])
        instance = self.queryset.get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    @extend_schema(
        summary="Delete a dish",
        description=(
            "Soft-deletes a dish by setting `is_deleted=True`. The dish will no longer appear in list responses."
        ),
        responses={200: OpenApiResponse(description="Dish deleted successfully")},
        examples=[
            OpenApiExample(
                name="Successful deletion",
                value={
                    "success": True,
                    "data": {},
                    "message": "Dish deleted successfully",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Dishes"],
    )
    def destroy(self, request, *args, **kwargs) -> Response:
        instance: DishModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return self.success(message=SuccessMessageEnum.DISH_DELETED)


class DrinkView(StandardizedResponseMixin, IngredientsEndpointMixin, ModelViewSet):
    """
    Drink management for the authenticated restaurant (cooker).

    Provides CRUD operations, availability toggling, and ingredient listing
    for drinks belonging to the authenticated cooker.
    """

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

    @extend_schema(
        summary="Create a drink",
        description=(
            "Creates a new drink for the authenticated restaurant.\n\n"
            "This endpoint accepts **multipart/form-data** to allow photo uploads alongside JSON fields.\n\n"
            "**Fields:**\n"
            "- `photos` (file[], required): One or more drink images. The first image becomes the primary image.\n"
            "- `cooker` (int, required): The cooker ID.\n"
            "- `name` (string, required): Drink name.\n"
            "- `price` (float, required): Selling price.\n"
            "- `capacity` (int, required): Capacity value.\n"
            "- `unit` (string, required): Unit of capacity. One of `liter`, `centiliters`.\n"
            "- `country` (string, required): Country of origin.\n"
            "- `description` (string, optional): Drink description.\n"
            "- `is_suitable_for_quick_delivery` (bool, optional): Whether the drink supports quick delivery.\n"
            "- `is_suitable_for_scheduled_delivery` (bool, optional): Whether the drink supports scheduled delivery.\n"
            "- `ingredients` (JSON array, required): Array of `{code, name, category?, is_allergen?}` objects.\n"
            "- `nutritional_info` (JSON object, optional): `{calories, proteins, carbohydrates, fats, fiber}`."
        ),
        request={
            "multipart/form-data": DrinkPOSTSerializer,
        },
        responses={
            201: OpenApiResponse(response=DrinkPOSTSerializer, description="Drink created successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                name="Create a Ginger Juice",
                description="Example: creating a homemade drink with ingredients and photos.",
                value={
                    "cooker": 6,
                    "name": "Ginger Juice",
                    "description": "Fresh homemade ginger juice with lemon",
                    "price": 3.50,
                    "capacity": 33,
                    "unit": "centiliters",
                    "country": "cameroun",
                    "is_suitable_for_quick_delivery": True,
                    "is_suitable_for_scheduled_delivery": True,
                    "photos": ["(binary file)"],
                    "ingredients": [
                        {"code": "ginger", "name": "Ginger", "category": "spice", "is_allergen": False},
                        {"code": "lemon", "name": "Lemon", "category": "fruit", "is_allergen": False},
                        {"code": "sugar", "name": "Sugar", "category": "sweetener", "is_allergen": False},
                    ],
                    "nutritional_info": {
                        "calories": 80,
                        "proteins": 0.5,
                        "carbohydrates": 18.0,
                        "fats": 0.1,
                        "fiber": 0.3,
                    },
                },
                request_only=True,
                media_type="multipart/form-data",
            ),
            OpenApiExample(
                name="Response — Drink created",
                description="Successful creation response.",
                value={
                    "success": True,
                    "data": {
                        "id": 5,
                        "cooker": 6,
                        "name": "Ginger Juice",
                        "description": "Fresh homemade ginger juice with lemon",
                        "price": 3.50,
                        "capacity": 33,
                        "unit": "centiliters",
                        "country": "cameroun",
                        "is_suitable_for_quick_delivery": True,
                        "is_suitable_for_scheduled_delivery": True,
                        "ingredients": [
                            {"id": 1, "code": "ginger", "name": "Ginger", "category": "spice", "is_allergen": False},
                            {"id": 2, "code": "lemon", "name": "Lemon", "category": "fruit", "is_allergen": False},
                        ],
                        "nutritional_info": {
                            "calories": 80,
                            "proteins": 0.5,
                            "carbohydrates": 18.0,
                            "fats": 0.1,
                            "fiber": 0.3,
                        },
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
        tags=["Drinks"],
    )
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

    @extend_schema(
        summary="Full update a drink",
        description=(
            "Fully updates an existing drink. All required fields must be provided.\n\n"
            "Accepts **multipart/form-data**. Sending `photos` replaces all existing images."
        ),
        request={"multipart/form-data": DrinkPOSTSerializer},
        responses={200: OpenApiResponse(response=DrinkPOSTSerializer, description="Drink updated")},
        tags=["Drinks"],
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

    @extend_schema(
        summary="Partially update a drink",
        description=(
            "Partially updates an existing drink. Only the provided fields are modified.\n\n"
            "Accepts **multipart/form-data**. Sending `photos` replaces all existing images."
        ),
        request={"multipart/form-data": DrinkPATCHSerializer},
        responses={200: OpenApiResponse(response=DrinkPATCHSerializer, description="Drink partially updated")},
        examples=[
            OpenApiExample(
                name="Update price",
                value={
                    "price": 4.50,
                },
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                name="Replace photos",
                value={
                    "photos": ["(binary file)", "(binary file)"],
                },
                request_only=True,
                media_type="multipart/form-data",
            ),
            OpenApiExample(
                name="Response — Drink updated",
                value={
                    "success": True,
                    "data": {
                        "name": "Ginger Juice",
                        "price": 4.50,
                        "description": "Fresh homemade ginger juice with lemon",
                        "ingredients": [
                            {"id": 1, "code": "ginger", "name": "Ginger", "category": "spice", "is_allergen": False},
                        ],
                        "nutritional_info": {},
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Drinks"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer: BaseSerializer) -> None:
        current_object = self.get_object()
        cooker_pk = str(current_object.cooker.pk)
        photos = self.request.FILES.getlist("photos") or self.request.FILES.getlist("photos[]")

        if photos:
            # Replace all existing images with the newly uploaded ones
            for old_image in current_object.images.all():
                if old_image.key and "default" not in old_image.key:
                    delete_s3_object(old_image.key)
            current_object.images.all().delete()

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

    @extend_schema(
        summary="Get drink details",
        description=(
            "Returns the full details of a drink, including all images, "
            "detailed ingredients, and nutritional information."
        ),
        responses={
            200: OpenApiResponse(response=DrinkDetailSerializer, description="Drink details"),
            404: OpenApiResponse(description="Drink not found"),
        },
        examples=[
            OpenApiExample(
                name="Drink detail — Ginger Juice",
                value={
                    "success": True,
                    "data": {
                        "id": 5,
                        "name": "Ginger Juice",
                        "description": "Fresh homemade ginger juice with lemon",
                        "price": 3.50,
                        "capacity": 33,
                        "unit": "centiliters",
                        "country": "cameroun",
                        "is_enabled": True,
                        "is_suitable_for_quick_delivery": True,
                        "is_suitable_for_scheduled_delivery": True,
                        "cooker": {
                            "id": 6,
                            "firstname": "Jean",
                            "lastname": "Dupont",
                            "email": "jean@reats.fr",
                            "acceptance_rate": 95.0,
                        },
                        "images": [
                            {
                                "id": 1,
                                "url": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/drinks/ginger.png?X-Amz-...",
                                "is_primary": True,
                                "position": 0,
                            },
                        ],
                        "ingredients": [
                            {"id": 1, "code": "ginger", "name": "Ginger", "category": "spice", "is_allergen": False},
                            {"id": 2, "code": "lemon", "name": "Lemon", "category": "fruit", "is_allergen": False},
                        ],
                        "ratings": [],
                        "nutritional_info": {
                            "calories": 80,
                            "proteins": 0.5,
                            "carbohydrates": 18.0,
                            "fats": 0.1,
                            "fiber": 0.3,
                        },
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Drinks"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    @extend_schema(
        summary="List drinks",
        description=(
            "Returns a paginated list of drinks for the authenticated restaurant.\n\n"
            "By default, only enabled drinks are returned. Use `is_enabled=false` to include disabled drinks.\n\n"
            "**Available filters:**\n"
            "- `search`: trigram text search on name and description\n"
            "- `is_enabled`: filter by availability (`true`/`false`)"
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Text search on drink name and description (trigram similarity)",
                required=False,
                examples=[OpenApiExample(name="Search for Ginger", value="Ginger")],
            ),
            OpenApiParameter(
                name="is_enabled",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by availability. Only enabled drinks are returned by default.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(response=DrinkListSerializer(many=True), description="Paginated drink list"),
        },
        examples=[
            OpenApiExample(
                name="Drink list response",
                value={
                    "success": True,
                    "data": {
                        "count": 2,
                        "next": None,
                        "previous": None,
                        "results": [
                            {
                                "id": 5,
                                "name": "Ginger Juice",
                                "description": "Fresh homemade ginger juice with lemon",
                                "price": 3.50,
                                "capacity": 33,
                                "unit": "centiliters",
                                "country": "cameroun",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": True,
                                "is_suitable_for_scheduled_delivery": True,
                                "cooker": {
                                    "id": 6,
                                    "firstname": "Jean",
                                    "lastname": "Dupont",
                                    "email": "jean@reats.fr",
                                    "acceptance_rate": 95.0,
                                },
                                "image": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/drinks/ginger.png?X-Amz-...",
                                "ingredients": [
                                    {
                                        "id": 1,
                                        "code": "ginger",
                                        "name": "Ginger",
                                        "category": "spice",
                                        "is_allergen": False,
                                    },
                                ],
                                "ratings": [],
                                "nutritional_info": {},
                            },
                            {
                                "id": 6,
                                "name": "Hibiscus Tea",
                                "description": "Traditional bissap drink",
                                "price": 2.99,
                                "capacity": 50,
                                "unit": "centiliters",
                                "country": "cameroun",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": True,
                                "is_suitable_for_scheduled_delivery": False,
                                "cooker": {
                                    "id": 6,
                                    "firstname": "Jean",
                                    "lastname": "Dupont",
                                    "email": "jean@reats.fr",
                                    "acceptance_rate": 95.0,
                                },
                                "image": "https://reats-dev-bucket.s3.eu-central-1.amazonaws.com/cookers/6/drinks/bissap.png?X-Amz-...",
                                "ingredients": [
                                    {
                                        "id": 3,
                                        "code": "hibiscus",
                                        "name": "Hibiscus",
                                        "category": "flower",
                                        "is_allergen": False,
                                    },
                                ],
                                "ratings": [],
                                "nutritional_info": {
                                    "calories": 45,
                                    "proteins": 0.2,
                                    "carbohydrates": 10.0,
                                    "fats": 0.0,
                                    "fiber": 0.1,
                                },
                            },
                        ],
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Drinks"],
    )
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

    @extend_schema(
        summary="Toggle drink availability",
        description=(
            "Toggles the `is_enabled` flag of a drink. "
            "If the drink is currently enabled, it becomes disabled and vice-versa.\n\n"
            "No request body is required."
        ),
        request=None,
        responses={200: OpenApiResponse(response=DrinkListSerializer, description="Drink with updated availability")},
        examples=[
            OpenApiExample(
                name="Drink disabled",
                value={
                    "success": True,
                    "data": {
                        "id": 5,
                        "name": "Ginger Juice",
                        "is_enabled": False,
                    },
                    "message": "Operation successful",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Drinks"],
    )
    @action(detail=True, methods=["patch"], url_path="availability")
    def toggle_availability(self, request, *args, **kwargs) -> Response:
        instance: DrinkModel = self.get_object()
        instance.is_enabled = not instance.is_enabled
        instance.save(
            update_fields=[
                "is_enabled",
            ]
        )
        instance = self.queryset.get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    @extend_schema(
        summary="Delete a drink",
        description=(
            "Soft-deletes a drink by setting `is_deleted=True`. The drink will no longer appear in list responses."
        ),
        responses={200: OpenApiResponse(description="Drink deleted successfully")},
        examples=[
            OpenApiExample(
                name="Successful deletion",
                value={
                    "success": True,
                    "data": {},
                    "message": "Drink deleted successfully",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        tags=["Drinks"],
    )
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


class LogoutView(StandardizedResponseMixin, APIView):
    permission_classes = [UserPermission]

    @extend_schema(
        request=inline_serializer(name="LogoutRequest", fields={"refresh": serializers.CharField()}),
        responses={200: OpenApiResponse(description="Successfully logged out.")},
        tags=["Auth"],
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return self.error(
                    ErrorMessageEnum.INVALID_DATA,
                    code=ErrorCodeEnum.MISSING_PARAMETERS,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return self.success(
                message=SuccessMessageEnum.LOGOUT_SUCCESSFUL,
                status_code=status.HTTP_200_OK,
            )
        except TokenError:
            return self.error(
                ErrorMessageEnum.INVALID_DATA,
                code=ErrorCodeEnum.INVALID_DATA,
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class CookerOrderView(
    StandardizedResponseMixin,
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    permission_classes = [UserPermission]
    pagination_class = StandardizedResultsSetPagination
    queryset = OrderModel.objects.all()

    VALID_ACTIVE_STATUSES = [
        OrderStatusEnum.PENDING,
        OrderStatusEnum.ACCEPTED,
        OrderStatusEnum.PREPARING,
        OrderStatusEnum.READY,
    ]

    @extend_schema(
        summary="Get order details",
        description="Returns the full details of an order for the authenticated cooker.",
        responses={
            200: OpenApiResponse(response=CookerOrderGETSerializer, description="Order details"),
            404: OpenApiResponse(description="Order not found"),
        },
        examples=[
            OpenApiExample(
                name="Order details example",
                value={
                    "success": True,
                    "message": "Operation successful",
                    "data": {
                        "id": 1582,
                        "status": "pending",
                        "created": "2026-05-15T08:41:18.646583Z",
                        "accepted_date": None,
                        "preparing_date": None,
                        "ready_date": None,
                        "delivering_date": None,
                        "completed_date": None,
                        "cancelled_date": None,
                        "cancelled_by": None,
                        "scheduled_delivery_date": None,
                        "is_scheduled": False,
                        "delivery_fees": 5.0,
                        "delivery_fees_bonus": None,
                        "delivery_distance": 1200.0,
                        "delivery_initial_distance": None,
                        "paid_date": "2026-05-15T08:40:50Z",
                        "rating": 0.0,
                        "comment": None,
                        "delivery_man": None,
                        "customer": {"id": 13, "firstname": "Jane", "lastname": "Smith"},
                        "address": {"id": 10, "postal_code": "75008", "town": "Paris"},
                        "dishes_items": [
                            {
                                "id": 44,
                                "name": "Homemade Burger",
                                "description": "Juicy beef burger with cheese and fresh vegetables.",
                                "price": 12.5,
                                "category": "dish",
                                "country": "France",
                                "image": "https://s3.../default_burger.jpg",
                                "is_enabled": True,
                                "is_suitable_for_quick_delivery": True,
                                "is_suitable_for_scheduled_delivery": True,
                                "cost": None,
                                "preparation_time": 20,
                                "max_concurrent_orders": 10,
                                "margin": None,
                                "ingredients": ["BEEF", "CHEESE", "LETTUCE", "TOMATO", "BREAD"],
                                "ratings": [
                                    {"rating": 5.0, "comment": "Excellent !"},
                                    {"rating": 4.0, "comment": "Très bon"},
                                ],
                                "cooker": {
                                    "id": 6,
                                    "firstname": "John",
                                    "lastname": "Doe",
                                    "email": "john@reats.fr",
                                    "acceptance_rate": 90.0,
                                },
                                "quantity": 1,
                            }
                        ],
                        "drinks_items": [
                            {
                                "id": 5,
                                "name": "Red Wine",
                                "description": "Full-bodied red wine.",
                                "price": 4.0,
                                "unit": "centiliters",
                                "capacity": 75,
                                "country": "France",
                                "is_enabled": True,
                                "available": True,
                                "image": "https://s3.../default_wine.jpg",
                                "ingredients": ["GRAPE"],
                                "ratings": [{"rating": 4.5, "comment": "Très agréable"}],
                                "nutritional_info": {
                                    "calories": 85,
                                    "proteins": 0.1,
                                    "carbohydrates": 2.6,
                                    "sugars": 0.6,
                                    "fats": 0.0,
                                    "saturated_fats": 0.0,
                                    "fiber": 0.0,
                                    "salt": 0.01,
                                    "sodium": 0.004,
                                },
                                "cost": None,
                                "margin": None,
                                "created_at": "2026-01-01T00:00:00Z",
                                "updated_at": "2026-01-01T00:00:00Z",
                                "quantity": 2,
                            }
                        ],
                        "items_count": 3,
                        "sub_total": 20.5,
                        "service_fees": 1.44,
                        "total_amount": 26.94,
                    },
                },
                response_only=True,
            )
        ],
        tags=["Cooker Orders"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success(serializer.data)

    def _perform_cooker_action(self, instance: OrderModel, new_status: OrderStatusEnum) -> Response:
        previous_status = instance.status
        if new_status == OrderStatusEnum.CANCELLED:
            instance.cancelled_by = CancelledByEnum.COOKER.value
        try:
            instance.transition_to(new_status)
        except ValueError as e:
            logger.error(e)
            return self.error(
                message=str(e),
                code=ErrorCodeEnum.TRANSITION_ERROR,
                status_code=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            logger.error(e)
            return self.error(
                message=ErrorMessageEnum.INTERNAL_SERVER_ERROR,
                code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if new_status == OrderStatusEnum.ACCEPTED:
            capture_payment_intent(instance)
        if new_status == OrderStatusEnum.CANCELLED:
            if previous_status == OrderStatusEnum.PENDING:
                cancel_payment_intent(instance)
            elif previous_status in (
                OrderStatusEnum.ACCEPTED,
                OrderStatusEnum.PREPARING,
                OrderStatusEnum.READY,
            ):
                amount_to_refund_in_cents = Decimal(
                    str(compute_order_items_total_amount(instance) + instance.delivery_fees)
                ) * Decimal("100")
                create_stripe_refund(int(amount_to_refund_in_cents), instance.stripe_payment_intent_id)
        update_cooker_acceptance_rate(instance, new_status)
        return self.success(CookerOrderGETSerializer(instance).data)

    @extend_schema(
        summary="Accept an order",
        description="Transitions the order from `pending` to `accepted`.",
        request=None,
        responses={
            200: OpenApiResponse(response=CookerOrderGETSerializer, description="Order accepted"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Invalid state transition"),
            500: OpenApiResponse(description="Internal server error"),
        },
        tags=["Cooker Orders"],
    )
    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, *args, **kwargs) -> Response:
        return self._perform_cooker_action(self.get_object(), OrderStatusEnum.ACCEPTED)

    @extend_schema(
        summary="Start preparing an order",
        description="Transitions the order from `accepted` to `preparing`.",
        request=None,
        responses={
            200: OpenApiResponse(response=CookerOrderGETSerializer, description="Order is now being prepared"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Invalid state transition"),
            500: OpenApiResponse(description="Internal server error"),
        },
        tags=["Cooker Orders"],
    )
    @action(detail=True, methods=["post"], url_path="start-preparation")
    def start_preparation(self, request, *args, **kwargs) -> Response:
        return self._perform_cooker_action(self.get_object(), OrderStatusEnum.PREPARING)

    @extend_schema(
        summary="Mark an order as ready",
        description="Transitions the order from `preparing` to `ready`.",
        request=None,
        responses={
            200: OpenApiResponse(response=CookerOrderGETSerializer, description="Order is ready for pickup"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Invalid state transition"),
            500: OpenApiResponse(description="Internal server error"),
        },
        tags=["Cooker Orders"],
    )
    @action(detail=True, methods=["post"], url_path="mark-ready")
    def mark_ready(self, request, *args, **kwargs) -> Response:
        return self._perform_cooker_action(self.get_object(), OrderStatusEnum.READY)

    @extend_schema(
        summary="Cancel an order",
        description=(
            "Transitions the order to `cancelled` from `pending`, `accepted`, `preparing`, or `ready`, "
            "and sets `cancelled_by` to `cooker`.\n\n"
            "Stripe handling depends on the previous status: a `pending` order is only authorized, so its "
            "authorization is released; an order cancelled from `accepted`, `preparing`, or `ready` was "
            "already captured, so it is refunded."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=CookerOrderGETSerializer, description="Order cancelled"),
            404: OpenApiResponse(description="Order not found"),
            409: OpenApiResponse(description="Invalid state transition"),
            500: OpenApiResponse(description="Internal server error"),
        },
        tags=["Cooker Orders"],
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, *args, **kwargs) -> Response:
        return self._perform_cooker_action(self.get_object(), OrderStatusEnum.CANCELLED)

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "list":
            self.serializer_class = CookerOrderListSerializer
        else:
            self.serializer_class = CookerOrderGETSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset().filter(cooker__id=self.request.user.pk)

    @extend_schema(
        summary="List active orders",
        description=(
            "Returns a paginated list of active orders for the authenticated cooker.\n\n"
            "Active orders are those in `pending`, `accepted`, or `preparing` status.\n"
            "Defaults to `pending` if no status filter is provided."
        ),
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by order status. Defaults to `pending`.",
                required=False,
                enum=["pending", "accepted", "preparing", "ready"],
            ),
        ],
        responses={
            200: OpenApiResponse(response=CookerOrderListSerializer(many=True), description="List of active orders"),
            400: OpenApiResponse(description="Invalid status value"),
        },
        examples=[
            OpenApiExample(
                name="Active orders list",
                value={
                    "success": True,
                    "message": "Operation successful",
                    "data": {
                        "results": [
                            {
                                "id": 1582,
                                "status": "pending",
                                "created": "2026-05-15T08:41:18Z",
                                "customer": {"id": 13, "firstname": "Jane", "lastname": "Smith"},
                                "address": {"id": 10, "postal_code": "75008", "town": "Paris"},
                                "dishes_items": [
                                    {
                                        "id": 44,
                                        "name": "Homemade Burger",
                                        "category": "dish",
                                        "image": "https://s3.../default_burger.jpg",
                                        "quantity": 1,
                                        "unit_price": 12.5,
                                    }
                                ],
                                "drinks_items": [
                                    {
                                        "id": 5,
                                        "name": "Red Wine",
                                        "capacity": "75cl",
                                        "image": "https://s3.../default_wine.jpg",
                                        "quantity": 2,
                                        "unit_price": 4.0,
                                    }
                                ],
                                "items_count": 3,
                                "sub_total": 20.5,
                                "delivery_fees": 5.0,
                                "service_fees": 1.44,
                                "total_amount": 26.94,
                            }
                        ],
                        "pagination": {
                            "current_page": 1,
                            "total_pages": 1,
                            "total_items": 1,
                            "items_per_page": 10,
                        },
                    },
                },
                response_only=True,
            )
        ],
        tags=["Cooker Orders"],
    )
    def list(self, request, *args, **kwargs) -> Response:
        request_status = request.query_params.get("status", OrderStatusEnum.PENDING)

        if request_status not in self.VALID_ACTIVE_STATUSES:
            return self.error(
                message=f"Invalid status. Valid values: {[s.value for s in self.VALID_ACTIVE_STATUSES]}",
                code=ErrorCodeEnum.INVALID_ORDER_STATUS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset()).filter(status=request_status).order_by("-modified")

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
            OrderStatusEnum.COMPLETED,
            OrderStatusEnum.CANCELLED,
            OrderStatusEnum.NOT_ACCEPTED,
        ]
    )

    pagination_class = StandardizedResultsSetPagination
    serializer_class = CookerOrderHistorySerializer

    VALID_HISTORY_STATUSES = [
        OrderStatusEnum.COMPLETED,
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.NOT_ACCEPTED,
    ]

    VALID_CANCELLED_BY = [
        CancelledByEnum.COOKER,
        CancelledByEnum.CUSTOMER,
        CancelledByEnum.SYSTEM,
    ]

    def get_queryset(self):
        return super().get_queryset().filter(cooker__id=self.request.user.pk)

    @extend_schema(
        summary="List order history",
        description=(
            "Returns a paginated list of past orders (completed, cancelled or not accepted)"
            " for the authenticated cooker.\n\n"
            "Use the `cancelled_by` field in the response to distinguish who cancelled the order "
            '(`"cooker"`, `"customer"` or `"system"`).\n\n'
            "Optionally filter by `status`, `cancelled_by`, and/or a date range (`start_date` / `end_date`).\n\n"
            "The `cooker` field is not included — the authenticated cooker's identity is available from the JWT token."
        ),
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by order status.",
                required=False,
                enum=["completed", "cancelled", "not_accepted"],
            ),
            OpenApiParameter(
                name="cancelled_by",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter cancelled orders by who initiated the cancellation.",
                required=False,
                enum=["cooker", "customer", "system"],
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter orders created after this date (ISO format).",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Filter orders created before this date (ISO format).",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(response=CookerOrderHistorySerializer(many=True), description="List of past orders"),
        },
        examples=[
            OpenApiExample(
                name="Order history list",
                value={
                    "success": True,
                    "message": "Operation successful",
                    "data": {
                        "results": [
                            {
                                "id": 1582,
                                "status": "completed",
                                "created": "2026-05-10T15:00:00Z",
                                "accepted_date": "2026-05-10T15:05:00Z",
                                "preparing_date": "2026-05-10T15:10:00Z",
                                "ready_date": "2026-05-10T15:30:00Z",
                                "delivering_date": "2026-05-10T15:45:00Z",
                                "completed_date": "2026-05-10T16:00:00Z",
                                "cancelled_date": None,
                                "cancelled_by": None,
                                "scheduled_delivery_date": None,
                                "is_scheduled": False,
                                "delivery_fees": 5.0,
                                "delivery_fees_bonus": None,
                                "delivery_distance": 1200.0,
                                "delivery_initial_distance": None,
                                "paid_date": "2026-05-10T14:58:00Z",
                                "rating": 4.5,
                                "comment": "Très bon repas !",
                                "delivery_man": 3,
                                "customer": {"id": 13, "firstname": "Jane", "lastname": "Smith"},
                                "address": {"id": 10, "postal_code": "75008", "town": "Paris"},
                                "dishes_items": [
                                    {
                                        "id": 44,
                                        "name": "Homemade Burger",
                                        "description": "Juicy beef burger.",
                                        "price": 12.5,
                                        "category": "dish",
                                        "country": "France",
                                        "image": "https://s3.../default_burger.jpg",
                                        "is_enabled": True,
                                        "is_suitable_for_quick_delivery": True,
                                        "is_suitable_for_scheduled_delivery": True,
                                        "cost": None,
                                        "preparation_time": 20,
                                        "max_concurrent_orders": 10,
                                        "margin": None,
                                        "ingredients": ["BEEF", "CHEESE", "LETTUCE", "TOMATO", "BREAD"],
                                        "ratings": [
                                            {"rating": 5.0, "comment": "Excellent !"},
                                            {"rating": 4.0, "comment": "Très bon"},
                                        ],
                                        "cooker": {
                                            "id": 6,
                                            "firstname": "John",
                                            "lastname": "Doe",
                                            "email": "john@reats.fr",
                                            "acceptance_rate": 90.0,
                                        },
                                        "quantity": 1,
                                    }
                                ],
                                "drinks_items": [],
                                "items_count": 1,
                                "sub_total": 12.5,
                                "service_fees": 0.88,
                                "total_amount": 18.38,
                            },
                            {
                                "id": 1241,
                                "status": "cancelled",
                                "created": "2026-05-08T12:00:00Z",
                                "accepted_date": None,
                                "preparing_date": None,
                                "ready_date": None,
                                "delivering_date": None,
                                "completed_date": None,
                                "cancelled_date": "2026-05-08T12:05:00Z",
                                "cancelled_by": "cooker",
                                "scheduled_delivery_date": None,
                                "is_scheduled": False,
                                "delivery_fees": 3.5,
                                "delivery_fees_bonus": None,
                                "delivery_distance": None,
                                "delivery_initial_distance": None,
                                "paid_date": "2026-05-08T11:58:00Z",
                                "rating": 0.0,
                                "comment": None,
                                "delivery_man": None,
                                "customer": {"id": 8, "firstname": "Marc", "lastname": "Dupont"},
                                "address": {"id": 7, "postal_code": "69001", "town": "Lyon"},
                                "dishes_items": [],
                                "drinks_items": [],
                                "items_count": 0,
                                "sub_total": 0.0,
                                "service_fees": 0.0,
                                "total_amount": 3.5,
                            },
                        ],
                        "pagination": {
                            "current_page": 1,
                            "total_pages": 1,
                            "total_items": 2,
                            "items_per_page": 10,
                        },
                    },
                },
                response_only=True,
            )
        ],
        tags=["Cooker Orders"],
    )
    def list(self, request, *args, **kwargs) -> Response:
        order_status: Union[str, None] = request.query_params.get("status")
        cancelled_by: Union[str, None] = request.query_params.get("cancelled_by")
        start_date: Union[str, None] = request.query_params.get("start_date")
        end_date: Union[str, None] = request.query_params.get("end_date")

        if order_status and order_status not in self.VALID_HISTORY_STATUSES:
            return self.error(
                message=f"Invalid status. Valid values: {[s.value for s in self.VALID_HISTORY_STATUSES]}",
                code=ErrorCodeEnum.INVALID_ORDER_STATUS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if cancelled_by and cancelled_by not in self.VALID_CANCELLED_BY:
            return self.error(
                message=f"Invalid cancelled_by. Valid values: {[c.value for c in self.VALID_CANCELLED_BY]}",
                code=ErrorCodeEnum.INVALID_DATA,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset()).order_by("-modified")

        if order_status:
            queryset = queryset.filter(status=order_status)

        if cancelled_by:
            queryset = queryset.filter(cancelled_by=cancelled_by)

        if start_date and end_date:
            start_date_object = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_date_object = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if start_date_object > end_date_object:
                return self.error(
                    message=ErrorMessageEnum.INVALID_DATE_RANGE,
                    code=ErrorCodeEnum.INVALID_DATE_FORMAT,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(
                created__gte=start_date_object,
                created__lte=end_date_object,
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success(serializer.data, status_code=status.HTTP_200_OK)
