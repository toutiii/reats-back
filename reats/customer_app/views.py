import logging
from typing import Type, Union

from cooker_app.models import DishModel
from custom_renderers.renderers import CustomRendererWithData, CustomRendererWithoutData
from django.db import IntegrityError
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from utils.common import activate_user, format_phone, is_otp_valid, send_otp
from utils.custom_permissions import CustomAPIKeyPermission, UserPermission

from .models import CustomerModel
from .serializers import CustomerSerializer, DishGETSerializer

logger = logging.getLogger("watchtower-logger")


class CustomerView(ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = CustomerModel.objects.all()
    serializer_class = CustomerSerializer
    renderer_classes = [CustomRendererWithoutData]

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
            logger.info(f"Customer with phone {e164_phone_format} does not exist.")
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


class DishView(ListModelMixin, GenericViewSet):
    serializer_class = DishGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.all()

    def list(self, request, *args, **kwargs) -> Response:
        request_sort: Union[str, None] = self.request.query_params.get("sort")
        request_name: Union[str, None] = self.request.query_params.get("name")

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_sort is not None:
            if request_sort == "new":
                self.queryset = self.queryset.order_by("created")
            else:
                self.queryset = self.queryset.order_by("created")

        self.queryset.filter(is_enabled=True)

        if request_sort is None and request_name is None:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)
