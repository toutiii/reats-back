import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Type, Union

from core_app.models import CookerModel, DishModel, DrinkModel, OrderDishItemModel, OrderModel
from core_app.serializers import (
    DishGETSerializer,
    DrinkGETSerializer,
    OrderPATCHSerializer,
)
from django.db import IntegrityError
from django.db.models import Count, Sum
from django.utils import timezone
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.parsers import JSONParser, MultiPartParser
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
    get_pre_signed_url,
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
    OrderStatusEnum,
    SuccessMessageEnum,
)

from .serializers import (
    CookerGETSerializer,
    CookerOrderGETSerializer,
    CookerSerializer,
    DashboardStatsSerializer,
    DishPATCHSerializer,
    DishPOSTSerializer,
    DrinkPATCHSerializer,
    DrinkPOSTSerializer,
    TokenObtainPairWithoutPasswordSerializer,
    TokenObtainRefreshWithoutPasswordSerializer,
)

logger = logging.getLogger("watchtower-logger")


class CookerView(StandardizedResponseMixin, ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser]
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
        kwargs.pop("pk")  # pk is unexpected in parent's partial_update method
        cooker: CookerModel = self.get_object()
        old_photo_key: str = cooker.photo
        photo = None

        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            photo = "cookers" + "/" + str(cooker.pk) + "/" + "profile_pics" + "/" + self.request.FILES["photo"].name

        if photo is not None:
            upload_image_to_s3(self.request.FILES["photo"], photo)
            cooker.photo = photo
            cooker.save()

            if not old_photo_key.endswith("default-profile-pic.jpg"):
                delete_s3_object(old_photo_key)

        return super().partial_update(request, *args, **kwargs)

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
        period = request.query_params.get("period", "today")
        cooker_id = request.user.pk

        date_range = self._get_date_range(period)
        stats = self._calculate_stats(cooker_id, date_range)
        revenue_chart = self._generate_revenue_chart(cooker_id, period, date_range)
        recent_reviews = self._get_recent_reviews(cooker_id, limit=5)
        popular_items = self._get_popular_items(cooker_id, date_range, limit=5)

        data = {
            "period": period,
            "stats": stats,
            "revenueChart": revenue_chart,
            "recentReviews": recent_reviews,
            "popularItems": popular_items,
        }

        serializer = DashboardStatsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return self.success(data=serializer.data)

    def _get_date_range(self, period):
        now = timezone.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start = start_date - timedelta(days=1)
            prev_end = start_date
        elif period == "week":
            start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_end = start_date
            prev_start = (start_date - timedelta(days=1)).replace(day=1)
        elif period == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_end = start_date
            # Simple previous year
            prev_start = start_date.replace(year=start_date.year - 1)
        else:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_start = start_date - timedelta(days=1)
            prev_end = start_date

        return {"start": start_date, "end": now, "prev_start": prev_start, "prev_end": prev_end}

    def _calculate_stats(self, cooker_id, date_range):
        current_orders = OrderModel.objects.filter(
            cooker_id=cooker_id, created__gte=date_range["start"]
        ).prefetch_related("dishes_items__dish", "drinks_items__drink")
        prev_orders = OrderModel.objects.filter(
            cooker_id=cooker_id, created__gte=date_range["prev_start"], created__lt=date_range["prev_end"]
        ).prefetch_related("dishes_items__dish", "drinks_items__drink")

        # Active orders (current total regardless of period for the count, but let's stick to spec if it implies period)
        # Spec says "Active orders", usually means currently in progress.
        active_count = OrderModel.objects.filter(
            cooker_id=cooker_id,
            status__in=[OrderStatusEnum.PENDING, OrderStatusEnum.PROCESSING, OrderStatusEnum.COMPLETED],
        ).count()

        pending_count = OrderModel.objects.filter(cooker_id=cooker_id, status=OrderStatusEnum.PENDING).count()

        # Revenue for the period
        current_revenue = sum(
            compute_order_total_amount(o) for o in current_orders.filter(status=OrderStatusEnum.DELIVERED)
        )
        prev_revenue = sum(compute_order_total_amount(o) for o in prev_orders.filter(status=OrderStatusEnum.DELIVERED))

        # Customers served in the period
        current_customers = (
            current_orders.filter(status=OrderStatusEnum.DELIVERED).values("customer").distinct().count()
        )
        prev_customers = prev_orders.filter(status=OrderStatusEnum.DELIVERED).values("customer").distinct().count()

        return {
            "activeOrders": {"count": active_count, "trend": None},  # Trend for active orders is usually less relevant
            "pendingOrders": {"count": pending_count, "trend": None},
            "revenue": {
                "amount": current_revenue,
                "currency": "EUR",
                "trend": self._calculate_trend(current_revenue, prev_revenue),
            },
            "customersServed": {
                "count": current_customers,
                "trend": self._calculate_trend(current_customers, prev_customers),
            },
        }

    def _generate_revenue_chart(self, cooker_id, period, date_range):
        labels = []
        data = []

        orders = (
            OrderModel.objects.filter(
                cooker_id=cooker_id, created__gte=date_range["start"], status=OrderStatusEnum.DELIVERED
            )
            .prefetch_related("dishes_items__dish", "drinks_items__drink")
            .order_by("created")
        )

        if period == "today":
            # 6 intervals of 4 hours
            intervals = [0, 4, 8, 12, 16, 20, 24]
            labels = ["00h-04h", "04h-08h", "08h-12h", "12h-16h", "16h-20h", "20h-24h"]
            for i in range(len(intervals) - 1):
                interval_total = sum(
                    compute_order_total_amount(o)
                    for o in orders.filter(created__hour__gte=intervals[i], created__hour__lt=intervals[i + 1])
                )
                data.append(float(interval_total))

        elif period == "week":
            days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
            labels = days
            # Sunday in weekday is 6, Monday is 0.
            for i in range(7):
                # ISO weekday starts 1 (Mon) to 7 (Sun)
                day_total = sum(compute_order_total_amount(o) for o in orders.filter(created__week_day=(i + 2) % 7 + 1))
                # Note: Django created__week_day is 1 (Sun) to 7 (Sat)
                # Map Lun(0) -> 2, Mar(1) -> 3... Dim(6) -> 1
                data.append(float(day_total))

        elif period == "month":
            # 4 weeks
            labels = ["Sem 1", "Sem 2", "Sem 3", "Sem 4"]
            for i in range(4):
                start = date_range["start"] + timedelta(days=i * 7)
                end = start + timedelta(days=7)
                week_total = sum(
                    compute_order_total_amount(o) for o in orders.filter(created__gte=start, created__lt=end)
                )
                data.append(float(week_total))

        elif period == "year":
            labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
            for i in range(1, 13):
                month_total = sum(compute_order_total_amount(o) for o in orders.filter(created__month=i))
                data.append(float(month_total))

        return {"labels": labels, "data": data}

    def _get_recent_reviews(self, cooker_id, limit=5):
        # Using OrderModel.rating and comment as per Option A
        orders_with_reviews = (
            OrderModel.objects.filter(cooker_id=cooker_id, rating__gt=0)
            .exclude(comment__isnull=True)
            .exclude(comment="")
            .select_related("customer")
            .order_by("-modified")[:limit]
        )

        reviews = []
        for o in orders_with_reviews:
            reviews.append(
                {
                    "id": str(o.id),
                    "customerName": f"{o.customer.firstname} {o.customer.lastname}",
                    "rating": int(o.rating),
                    "comment": o.comment,
                    "date": o.modified,
                    "orderNumber": f"#{o.id}",
                }
            )
        return reviews

    def _get_popular_items(self, cooker_id, date_range, limit=5):
        # Aggregate dish items

        dish_items = (
            OrderDishItemModel.objects.filter(
                order__cooker_id=cooker_id,
                order__created__gte=date_range["start"],
                order__status=OrderStatusEnum.DELIVERED,
            )
            .values("dish__id", "dish__name", "dish__photo", "dish__price")
            .annotate(total_sold=Sum("dish_quantity"))
            .order_by("-total_sold")[:limit]
        )

        popular = []
        for item in dish_items:
            popular.append(
                {
                    "id": str(item["dish__id"]),
                    "name": item["dish__name"],
                    "soldToday": item["total_sold"],
                    "revenue": Decimal(str(item["dish__price"])) * item["total_sold"],
                    "image": get_pre_signed_url(item["dish__photo"]),
                }
            )

        # Note: Ideally we would also include drinks and merge/sort, but for now we focus on dishes as per common logic
        # and to stay within limit. If drinks are needed, we would merge and sort the list.
        return popular[:limit]

    def _calculate_trend(self, current, previous):
        if not previous or previous == 0:
            return None
        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.0f}%"


class DishView(StandardizedResponseMixin, ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.filter(is_deleted=False).all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DishPOSTSerializer

        if self.request.method == "PATCH":
            self.serializer_class = DishPATCHSerializer

        if self.request.method == "GET":
            self.serializer_class = DishGETSerializer

        return super().get_serializer_class()

    def perform_create(self, serializer: BaseSerializer) -> None:
        photo = (
            "cookers"
            + "/"
            + str(serializer.validated_data["cooker"].pk)
            + "/"
            + "dishes"
            + "/"
            + serializer.validated_data["category"]
            + "/"
            + self.request.FILES["photo"].name
        )

        upload_image_to_s3(self.request.FILES["photo"], photo)
        serializer.validated_data["photo"] = photo
        super().perform_create(serializer)

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

    def perform_update(self, serializer: BaseSerializer) -> None:
        current_object = self.get_object()
        photo = None

        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            photo = (
                "cookers"
                + "/"
                + str(serializer.validated_data["cooker"].pk)
                + "/"
                + "dishes"
                + "/"
                + serializer.validated_data["category"]
                + "/"
                + self.request.FILES["photo"].name
            )

        if photo is not None:
            upload_image_to_s3(self.request.FILES["photo"], photo)
            serializer.validated_data["photo"] = photo
            old_photo_key = current_object.photo
            delete_s3_object(old_photo_key)

        super().perform_update(serializer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return self.success(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success(data=serializer.data)

    def list(self, request, *args, **kwargs) -> Response:
        request_name: Union[str, None] = self.request.query_params.get("name")
        request_category: Union[str, None] = self.request.query_params.get("category")
        request_status: Union[str, None] = self.request.query_params.get("is_enabled", "true")

        self.queryset = self.queryset.filter(cooker__id=request.user.pk)

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_category is not None:
            self.queryset = self.queryset.filter(category__in=request_category.split(","))

        if request_status is not None:
            self.queryset = self.queryset.filter(is_enabled=json.loads(request_status))

        if request_name is None and request_category is None and request_status is None:
            self.queryset = DishModel.objects.all()

        self.queryset = self.queryset.order_by("name")

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success(data=serializer.data)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: DishModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return self.success(message=SuccessMessageEnum.DISH_DELETED)


class DrinkView(StandardizedResponseMixin, ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DrinkModel.objects.filter(is_deleted=False).all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DrinkPOSTSerializer

        if self.request.method == "PATCH":
            self.serializer_class = DrinkPATCHSerializer

        if self.request.method == "GET":
            self.serializer_class = DrinkGETSerializer

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

    def perform_create(self, serializer: BaseSerializer) -> None:
        photo = (
            "cookers"
            + "/"
            + str(serializer.validated_data["cooker"].pk)
            + "/"
            + "drinks"
            + "/"
            + self.request.FILES["photo"].name
        )

        upload_image_to_s3(self.request.FILES["photo"], photo)
        serializer.validated_data["photo"] = photo
        super().perform_create(serializer)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        if not serializer.is_valid():
            return self.error(
                message="Invalid data",
                code="INVALID_DATA",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return self.success(data=serializer.data, status_code=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return self.error(
                message="Invalid data",
                code="INVALID_DATA",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return self.success(data=serializer.data, status_code=status.HTTP_200_OK)

    def perform_update(self, serializer: BaseSerializer) -> None:
        current_object = self.get_object()
        photo = None

        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            photo = (
                "cookers"
                + "/"
                + str(serializer.validated_data["cooker"].pk)
                + "/"
                + "drinks"
                + "/"
                + self.request.FILES["photo"].name
            )

        if photo is not None:
            upload_image_to_s3(self.request.FILES["photo"], photo)
            serializer.validated_data["photo"] = photo
            old_photo_key = current_object.photo
            delete_s3_object(old_photo_key)

        super().perform_update(serializer)

    def list(self, request, *args, **kwargs) -> Response:
        request_name: Union[str, None] = self.request.query_params.get("name")
        request_status: Union[str, None] = self.request.query_params.get("is_enabled", "true")

        self.queryset = self.queryset.filter(cooker__id=request.user.pk)

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_status is not None:
            self.queryset = self.queryset.filter(is_enabled=json.loads(request_status))

        if request_name is None and request_status is None:
            self.queryset = DrinkModel.objects.all()

        self.queryset = self.queryset.order_by("name")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success(data=serializer.data, status_code=status.HTTP_200_OK)

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
    parser_classes = [MultiPartParser]

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
    parser_classes = [MultiPartParser]
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
