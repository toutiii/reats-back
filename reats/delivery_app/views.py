import logging
from typing import Type, Union

from custom_renderers.renderers import (
    CustomRendererWithoutData,
    DeliverCustomRendererWithData,
    DeliveryStatsCustomRendererWithData,
)
from customer_app.models import OrderModel
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
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

from .models import DeliverModel
from .serializers import DeliverGETSerializer, DeliverSerializer

logger = logging.getLogger("watchtower-logger")


class DeliverView(ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DeliverModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PATCH"):
            self.serializer_class = DeliverSerializer

        if self.request.method == "GET":
            self.serializer_class = DeliverGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PATCH", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [DeliverCustomRendererWithData]

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
        customer: DeliverModel = self.get_object()
        old_photo_key: str = customer.photo
        new_photo_key = None

        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            new_photo_key = (
                "delivers"
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
        instance: DeliverModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )

    @action(methods=["post"], detail=False, url_path="otp-verify")
    def otp_verify(self, request) -> Response:
        # return Response(status=status.HTTP_200_OK)
        result = is_otp_valid(request.data)

        if result:
            activate_user(DeliverModel, request.data)
            return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="otp/ask")
    def ask_otp(self, request) -> Response:
        # return Response(status=status.HTTP_200_OK)
        phone = request.data.get("phone")

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            DeliverModel.objects.get(phone=e164_phone_format)
        except DeliverModel.DoesNotExist:
            logger.error(f"Customer with phone {e164_phone_format} does not exist.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        send_otp(e164_phone_format)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False)
    def auth(self, request) -> Response:
        # return Response(status=status.HTTP_200_OK)
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
            customer: DeliverModel = DeliverModel.objects.get(phone=e164_phone_format)
        except DeliverModel.DoesNotExist:
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


class DeliveryOrderStatsView(GenericViewSet, ListModelMixin):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all().filter(status="delivered")
    parser_classes = [MultiPartParser]
    renderer_classes = [DeliveryStatsCustomRendererWithData]

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(delivery_man__id=request.user.pk)
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if not all([start_date, end_date]):
            self.queryset = OrderModel.objects.none()

        if start_date:
            try:
                self.queryset = self.queryset.filter(created__gte=start_date)
            except DjangoValidationError as err:
                logger.error(err)
                self.queryset = OrderModel.objects.none()

        if end_date:
            try:
                self.queryset = self.queryset.filter(created__lte=end_date)
            except DjangoValidationError as err:
                logger.error(err)
                self.queryset = OrderModel.objects.none()

        if self.queryset.count() == 0:
            return Response(
                {
                    "ok": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                }
            )

        stats = {}
        stats["total_delivery_fees"] = 0.0
        stats["total_delivery_time"] = 0.0
        stats["total_delivery_distance"] = 0.0

        for order in self.queryset:
            stats["total_delivery_fees"] += (
                order.delivery_fees + order.delivery_fees_bonus
            )
            stats["total_delivery_time"] += (
                order.delivered_date - order.delivery_in_progress_date
            ).total_seconds()
            stats["total_delivery_distance"] += (
                order.delivery_distance + order.delivery_initial_distance
            )

        stats["total_delivery_fees"] = round(stats["total_delivery_fees"], 2)
        stats["total_delivery_distance"] = round(stats["total_delivery_distance"], 2)
        stats["total_number_of_deliveries"] = self.queryset.count()
        stats["delivery_mean_time"] = round(
            stats["total_delivery_time"] / stats["total_number_of_deliveries"], 2
        )
        del stats["total_delivery_time"]

        return Response(
            {
                "data": stats,
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )
