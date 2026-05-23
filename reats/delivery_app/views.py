import logging
from typing import Type, Union

from core_app.models import DeliverModel, OrderModel
from customer_app.serializers import OrderGETSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
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
from utils.common import (
    activate_user,
    delete_s3_object,
    format_phone,
    is_otp_valid,
    send_otp,
    upload_image_to_s3,
)
from utils.custom_api_reponse import StandardizedResponseMixin
from utils.custom_permissions import CustomAPIKeyPermission, UserPermission
from utils.enums import ErrorCodeEnum, ErrorMessageEnum, OrderStatusEnum

from .serializers import DeliverGETSerializer, DeliverSerializer

logger = logging.getLogger("watchtower-logger")


class DeliverView(StandardizedResponseMixin, ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DeliverModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PATCH"):
            self.serializer_class = DeliverSerializer

        if self.request.method == "GET":
            self.serializer_class = DeliverGETSerializer

        return super().get_serializer_class()

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
        super().perform_create(serializer)
        send_otp(serializer.validated_data.get("phone"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return self.success(data=serializer.data, status_code=status.HTTP_201_CREATED, headers=headers)
        except IntegrityError as err:
            logger.error(f"Deliver creation failed - duplicate phone number: {err}")
            return self.error(
                message=ErrorMessageEnum.CUSTOMER_ALREADY_EXISTS,
                code=ErrorCodeEnum.USER_ALREADY_EXISTS,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs) -> Response:
        try:
            instance = self.get_object()
            old_photo_key = instance.photo
            new_photo_key = None

            # Gestion de la photo
            if "photo" in request.FILES:
                new_photo_key = f"delivers/{instance.pk}/profile_pics/{request.FILES['photo'].name}"
                upload_image_to_s3(request.FILES["photo"], new_photo_key)
                instance.photo = new_photo_key
                instance.save()

                if not old_photo_key.endswith("default-profile-pic.jpg") and old_photo_key != new_photo_key:
                    delete_s3_object(old_photo_key)

            # Validation et mise à jour
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Réponse standardisée
            output_serializer = self.get_serializer(instance)
            return self.success(data=output_serializer.data, status_code=status.HTTP_200_OK)

        except ValidationError as e:
            return self.error(
                message=ErrorMessageEnum.VALIDATION_FAILED,
                code=ErrorCodeEnum.VALIDATION_ERROR,
                details=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error in partial_update: {e}")
            return self.error(
                message=ErrorMessageEnum.INTERNAL_SERVER_ERROR,
                code=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: DeliverModel = self.get_object()
        instance.is_deleted = True
        instance.save()

        return self.success(status_code=status.HTTP_200_OK)

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
            otp_response.get("MessageResponse", {}).get("Result", {}).get(e164_phone_format, {}).get("StatusCode")
        )

        if otp_response_status_code != status.HTTP_200_OK:
            logger.error(f"Failed to send an OTP to {e164_phone_format}")
            logger.error(f"Expected {status.HTTP_200_OK} but got {otp_response_status_code} in otp response")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        otp_response_delivery_status = (
            otp_response.get("MessageResponse", {}).get("Result", {}).get(e164_phone_format, {}).get("DeliveryStatus")
        )

        if otp_response_delivery_status != "SUCCESSFUL":
            logger.error(f"Failed to send an OTP to {e164_phone_format}")
            logger.error(f"Expected SUCCESSFUL but got {otp_response_delivery_status} in otp elivery status")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return self.success(data=serializer.data, status_code=status.HTTP_200_OK)


class DeliveryOrderStatsView(StandardizedResponseMixin, GenericViewSet, ListModelMixin):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all().filter(status=OrderStatusEnum.COMPLETED)
    parser_classes = [MultiPartParser]

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(delivery_man__id=request.user.pk)
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if not all([start_date, end_date]):
            self.queryset = OrderModel.objects.none()

        try:
            if start_date:
                self.queryset = self.queryset.filter(created__gte=start_date)
            if end_date:
                self.queryset = self.queryset.filter(created__lte=end_date)
        except (DjangoValidationError, ValueError) as err:
            logger.error(f"Invalid date format: {err}")
            return self.success(data={}, status_code=status.HTTP_200_OK)

        if self.queryset.count() == 0:
            return self.success(data={}, status_code=status.HTTP_200_OK)

        stats = {}
        stats["total_delivery_fees"] = 0.0
        stats["total_delivery_time"] = 0.0
        stats["total_delivery_distance"] = 0.0

        for order in self.queryset:
            stats["total_delivery_fees"] += order.delivery_fees + order.delivery_fees_bonus
            stats["total_delivery_time"] += (
                (order.completed_date - order.delivering_date).total_seconds()
                if order.completed_date and order.delivering_date
                else 0
            )
            stats["total_delivery_distance"] += order.delivery_distance + order.delivery_initial_distance

        stats["total_delivery_fees"] = round(stats["total_delivery_fees"], 2)
        stats["total_delivery_distance"] = round(stats["total_delivery_distance"], 2)
        stats["total_number_of_deliveries"] = self.queryset.count()
        stats["delivery_mean_time"] = round(stats["total_delivery_time"] / stats["total_number_of_deliveries"], 2)
        del stats["total_delivery_time"]

        return self.success(data=stats, status_code=status.HTTP_200_OK)


class DeliveryHistoryView(StandardizedResponseMixin, ListModelMixin, GenericViewSet):
    permission_classes = [UserPermission]
    queryset = OrderModel.objects.all().filter(status=OrderStatusEnum.COMPLETED)
    parser_classes = [MultiPartParser]
    serializer_class = OrderGETSerializer

    def list(self, request, *args, **kwargs) -> Response:
        self.queryset = self.queryset.filter(customer__id=request.user.pk)
        start_date = self.request.query_params.get("start_date")

        if start_date:
            try:
                self.queryset = self.queryset.filter(created__gte=start_date)
            except DjangoValidationError as err:
                logger.error(err)
                self.queryset = OrderModel.objects.none()

        response = super().list(request, *args, **kwargs)
        return self.success(
            data=response.data,
            status_code=status.HTTP_200_OK,
        )
