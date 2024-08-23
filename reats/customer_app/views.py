import logging
from typing import Type, Union

from cooker_app.models import CookerModel, DishModel, DrinkModel
from custom_renderers.renderers import (
    AddressCustomRendererWithData,
    CustomerCustomRendererWithData,
    CustomRendererWithData,
    CustomRendererWithoutData,
    DishesCountriesCustomRendererWithData,
    OrderCustomRendererWithData,
    OrderHistoryCustomRendererWithData,
)
from django.conf import settings
from django.db import IntegrityError
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from utils.common import (
    activate_user,
    delete_s3_object,
    format_phone,
    is_otp_valid,
    send_otp,
    upload_image_to_s3,
)
from utils.custom_permissions import CustomAPIKeyPermission, UserPermission
from utils.distance_computer import (
    compute_distance,
    get_closest_cookers_ids_from_customer_search_address,
)
from utils.distance_ratio import get_distance_radio

from .models import AddressModel, CustomerModel, OrderModel
from .serializers import (
    AddressGETSerializer,
    AddressSerializer,
    CustomerGETSerializer,
    CustomerSerializer,
    DishCountriesGETSerializer,
    DishGETSerializer,
    DrinkGETSerializer,
    OrderGETSerializer,
    OrderHistoryGETSerializer,
    OrderSerializer,
)

logger = logging.getLogger("watchtower-logger")


class CustomerView(ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = CustomerModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PATCH"):
            self.serializer_class = CustomerSerializer

        if self.request.method == "GET":
            self.serializer_class = CustomerGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PATCH", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CustomerCustomRendererWithData]

        return super().get_renderers()

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

    def perform_create(self, serializer: BaseSerializer) -> None:
        try:
            super().perform_create(serializer)
        except IntegrityError as err:
            logger.error(err)
            raise ValidationError("Integrity error occurred during customer creation.")

        send_otp(serializer.validated_data.get("phone"))

    def partial_update(self, request, *args, **kwargs) -> Response:
        kwargs.pop("pk")  # pk is unexpected in parent's partial_update method
        customer: CustomerModel = self.get_object()
        old_photo_key: str = customer.photo
        new_photo_key = None

        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            new_photo_key = (
                "customers"
                + "/"
                + str(customer.pk)
                + "/"
                + "profile_pics"
                + "/"
                + self.request.FILES["photo"].name
            )

        if new_photo_key is not None:
            upload_image_to_s3(self.request.FILES["photo"], new_photo_key)
            customer.photo = new_photo_key
            customer.save()

            if not old_photo_key.endswith("default-profile-pic.jpg"):
                if old_photo_key != new_photo_key:
                    delete_s3_object(old_photo_key)

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        super().perform_destroy(instance)

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )

    @action(methods=["post"], detail=False, url_path="otp-verify")
    def otp_verify(self, request) -> Response:
        result = is_otp_valid(request.data)

        if result:
            activate_user(CustomerModel, request.data)
            return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="otp/ask")
    def ask_otp(self, request) -> Response:
        phone = request.data.get("phone")

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            CustomerModel.objects.get(phone=e164_phone_format)
        except CustomerModel.DoesNotExist:
            logger.error(f"Customer with phone {e164_phone_format} does not exist.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        send_otp(e164_phone_format)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False)
    def auth(self, request) -> Response:
        phone = request.data.get("phone")

        if phone is None:
            logger.info("Missing phone number")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            logger.error("Wrong format for phone number")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            customer: CustomerModel = CustomerModel.objects.get(phone=e164_phone_format)
        except CustomerModel.DoesNotExist:
            logger.error(f"Customer with phone {e164_phone_format} does not exist.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not customer.is_activated:
            logger.error(f"Customer with phone {e164_phone_format} is not activated.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        otp_response: Union[dict, None] = send_otp(e164_phone_format)

        if otp_response is None:
            logger.error(f"Failed to send an OTP to {e164_phone_format}")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        otp_response_status_code = (
            otp_response.get("MessageResponse", {})
            .get("Result", {})
            .get(e164_phone_format, {})
            .get("StatusCode")
        )

        if otp_response_status_code != status.HTTP_200_OK:
            logger.error(f"Failed to send an OTP to {e164_phone_format}")
            logger.error(
                f"Expected {status.HTTP_200_OK} but got {otp_response_status_code} in otp response"
            )
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        otp_response_delivery_status = (
            otp_response.get("MessageResponse", {})
            .get("Result", {})
            .get(e164_phone_format, {})
            .get("DeliveryStatus")
        )

        if otp_response_delivery_status != "SUCCESSFUL":
            logger.error(f"Failed to send an OTP to {e164_phone_format}")
            logger.error(
                f"Expected SUCCESSFUL but got {otp_response_delivery_status} in otp elivery status"
            )
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(status=status.HTTP_200_OK)


class AddressView(ModelViewSet):
    queryset = AddressModel.objects.all()
    parser_classes = [MultiPartParser]
    permission_classes = [UserPermission]

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PUT", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [AddressCustomRendererWithData]

        return super().get_renderers()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = AddressSerializer

        if self.request.method == "GET":
            self.serializer_class = AddressGETSerializer

        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: AddressModel = self.get_object()
        instance.is_enabled = False
        instance.save()

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(customer__id=request.user.pk).filter(
            is_enabled=True
        )
        return super().list(request, *args, **kwargs)


class DishView(ListModelMixin, GenericViewSet):
    serializer_class = DishGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.filter(category="dish").all()

    def list(self, request, *args, **kwargs) -> Response:
        request_sort: Union[str, None] = self.request.query_params.get("sort")
        request_name: Union[str, None] = self.request.query_params.get("name")
        request_category: Union[str, None] = self.request.query_params.get("category")
        request_country: Union[str, None] = self.request.query_params.get("country")
        request_search_radius: Union[str, None] = self.request.query_params.get(
            "search_radius",
            "10",
        )
        request_address_id: Union[str, None] = self.request.query_params.get(
            "search_address_id"
        )
        request_delivery_mode: Union[str, None] = self.request.query_params.get(
            "delivery_mode"
        )
        request_cooker_id: Union[str, None] = self.request.query_params.get("cooker_id")
        closest_cookers_ids: list = []

        if request_address_id is None:
            logger.error("search_address_id is mandatory to run a search")
            return Response(
                {
                    "error": "search_address_id is mandatory to run a search",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_category is not None:
            self.queryset = self.queryset.filter(category=request_category)

        if request_country is not None:
            self.queryset = self.queryset.filter(country=request_country)

        if request_cooker_id is not None and request_cooker_id.isnumeric():
            self.queryset = self.queryset.filter(cooker__id=request_cooker_id)

        if request_sort is not None:
            if request_sort == "new":
                self.queryset = self.queryset.order_by("created")
            elif request_sort == "famous":
                # TODO: change this we'll be able to know the most ordered dishes in user's town
                self.queryset = self.queryset.order_by("created")
            else:
                logger.error(f"Invalid sort value {request_sort}")
                self.queryset = DishModel.objects.none()

        if request_address_id is not None:
            customer_address: AddressModel = AddressModel.objects.get(
                pk=request_address_id
            )
            closest_cookers_ids = get_closest_cookers_ids_from_customer_search_address(
                str(customer_address),
                CookerModel.objects.filter(
                    postal_code__startswith=customer_address.postal_code[:2]
                ),
                (
                    int(request_search_radius)
                    if request_search_radius
                    else settings.DEFAULT_SEARCH_RADIUS
                ),
            )

        if not closest_cookers_ids:
            self.queryset = DishModel.objects.none()
            return super().list(request, *args, **kwargs)

        if request_delivery_mode is not None:
            if request_delivery_mode == "now":
                self.queryset = self.queryset.filter(
                    is_suitable_for_quick_delivery=True
                )
            elif request_delivery_mode == "scheduled":
                self.queryset = self.queryset.filter(
                    is_suitable_for_scheduled_delivery=True
                )
            else:
                logger.error(f"Invalid delivery mode {request_delivery_mode}")
                self.queryset = DishModel.objects.none()

        self.queryset = (
            self.queryset.filter(cooker__id__in=closest_cookers_ids)
            .filter(cooker__is_online=True)
            .filter(is_enabled=True)
        )

        if (
            request_sort is None
            and request_name is None
            and request_category is None
            and request_country is None
            and request_search_radius is None
            and request_delivery_mode is None
        ):
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)


class DrinkView(ListModelMixin, GenericViewSet):
    serializer_class = DrinkGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DrinkModel.objects.all()

    def list(self, request, *args, **kwargs) -> Response:
        request_cooker_id: Union[str, int, None] = self.request.query_params.get(
            "cooker_id"
        )
        request_cooker_ids: list = self.request.query_params.get(
            "cooker_ids", ""
        ).split(",")
        request_cooker_ids = [item for item in request_cooker_ids if item]

        if request_cooker_ids:
            self.queryset = self.queryset.filter(cooker__id__in=request_cooker_ids)

        if request_cooker_id is not None:
            self.queryset = self.queryset.filter(cooker__id=request_cooker_id)

        self.queryset = self.queryset.filter(is_enabled=True)

        if request_cooker_id is None and not request_cooker_ids:
            self.queryset = DrinkModel.objects.none()

        return super().list(request, *args, **kwargs)


class DessertView(ListModelMixin, GenericViewSet):
    serializer_class = DishGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.filter(category="dessert").all()

    def list(self, request, *args, **kwargs) -> Response:
        request_cooker_id: Union[str, int, None] = self.request.query_params.get(
            "cooker_id"
        )
        request_cooker_ids: list = self.request.query_params.get(
            "cooker_ids", ""
        ).split(",")
        request_cooker_ids = [item for item in request_cooker_ids if item]

        if request_cooker_id is not None:
            self.queryset = self.queryset.filter(cooker__id=request_cooker_id)

        if request_cooker_ids:
            self.queryset = self.queryset.filter(cooker__id__in=request_cooker_ids)

        self.queryset = self.queryset.filter(is_enabled=True)

        if request_cooker_id is None and not request_cooker_ids:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)


class StarterView(ListModelMixin, GenericViewSet):
    serializer_class = DishGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.filter(category="starter").all()

    def list(self, request, *args, **kwargs) -> Response:
        request_cooker_id: Union[str, int, None] = self.request.query_params.get(
            "cooker_id"
        )
        request_cooker_ids: list = self.request.query_params.get(
            "cooker_ids", ""
        ).split(",")
        request_cooker_ids = [item for item in request_cooker_ids if item]

        if request_cooker_id is not None:
            self.queryset = self.queryset.filter(cooker__id=request_cooker_id)

        if request_cooker_ids:
            self.queryset = self.queryset.filter(cooker__id__in=request_cooker_ids)

        self.queryset = self.queryset.filter(is_enabled=True)

        if request_cooker_id is None and not request_cooker_ids:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)


class OrderView(CreateModelMixin, ListModelMixin, GenericViewSet):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all()
    parser_classes = [MultiPartParser]

    def perform_create(self, serializer: BaseSerializer) -> None:
        distance_dict: dict = compute_distance(
            origins=[str(serializer.validated_data.get("address"))],
            destinations=[
                serializer.validated_data.get("items")[0]["dish"].cooker.full_address
            ],  # As on order is bound to only one cooker, fetch the first item's cooker is enough
        )
        if distance_dict.get("status") == "KO":
            logger.error("Failed to compute distance")
            raise ValidationError("Failed to compute distance")

        order_instance: OrderModel = serializer.save()
        delivery_distance: float = distance_dict["rows"][0]["elements"][0]["distance"][
            "value"
        ]
        order_instance.delivery_distance = delivery_distance
        order_instance.delivery_fees = delivery_distance * get_distance_radio(
            delivery_distance
        )

        if serializer.validated_data.get("scheduled_delivery_date"):
            order_instance.is_scheduled = True

        order_instance.save()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PUT", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [OrderCustomRendererWithData]

        return super().get_renderers()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = OrderSerializer

        if self.request.method == "GET":
            self.serializer_class = OrderGETSerializer

        return super().get_serializer_class()

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(customer__id=request.user.pk)
        request_status: Union[str, None] = self.request.query_params.get("status")

        if request_status is not None:
            self.queryset = self.queryset.filter(status=request_status)
        if request_status is None or request_status not in [
            "pending",
            "processing",
            "completed",
        ]:
            logger.error(f"Invalid status {request_status}")
            self.queryset = OrderModel.objects.none()

        return super().list(request, *args, **kwargs)


class HistoryOrderView(ListModelMixin, GenericViewSet):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all().filter(
        status__in=[
            "delivered",
            "cancelled_by_customer",
            "cancelled_by_cooker",
        ]
    )
    parser_classes = [MultiPartParser]
    renderer_classes = [OrderHistoryCustomRendererWithData]
    serializer_class = OrderHistoryGETSerializer

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(customer__id=request.user.pk)

        return super().list(request, *args, **kwargs)


class DishCountriesView(ListModelMixin, GenericViewSet):
    renderer_classes = [DishesCountriesCustomRendererWithData]
    serializer_class = DishCountriesGETSerializer
    queryset = (
        DishModel.objects.filter(is_enabled=True)
        .filter(category="dish")
        .order_by("country")
        .distinct("country")
    )

    def list(self, request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)
