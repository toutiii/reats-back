import logging
from typing import Type, Union

from cooker_app.models import DishModel, DrinkModel
from custom_renderers.renderers import (
    AddressCustomRendererWithData,
    CustomerCustomRendererWithData,
    CustomRendererWithData,
    CustomRendererWithoutData,
)
from django.db import IntegrityError
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
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

from .models import AddressModel, CustomerModel
from .serializers import (
    AddressGETSerializer,
    AddressSerializer,
    CustomerGETSerializer,
    CustomerSerializer,
    DishGETSerializer,
    DrinkGETSerializer,
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
        instance = self.get_object()
        super().perform_destroy(instance)

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(customer__id=request.user.pk)
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

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_category is not None:
            self.queryset = self.queryset.filter(category=request_category)

        if request_sort is not None:
            if request_sort == "new":
                self.queryset = self.queryset.order_by("created")
            else:
                self.queryset = self.queryset.order_by("created")

        self.queryset.filter(is_enabled=True)

        if request_sort is None and request_name is None and request_category is None:
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
