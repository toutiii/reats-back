import json
import logging
from datetime import datetime
from typing import Type, Union

from custom_renderers.renderers import (
    CookerCustomRendererWithData,
    CustomJSONRendererWithData,
    CustomRendererWithData,
    CustomRendererWithoutData,
)
from customer_app.models import OrderModel
from django.db import IntegrityError
from django.db.models import Count
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.views import TokenViewBase
from utils.common import (
    activate_user,
    delete_s3_object,
    format_phone,
    is_otp_valid,
    send_otp,
    upload_image_to_s3,
)
from utils.custom_permissions import CustomAPIKeyPermission, UserPermission
from utils.enums import OrderStatusEnum

from .models import CookerModel, DishModel, DrinkModel
from .serializers import (
    CookerGETSerializer,
    CookerSerializer,
    DishGETSerializer,
    DishPATCHSerializer,
    DishPOSTSerializer,
    DrinkGETSerializer,
    DrinkPATCHSerializer,
    DrinkPOSTSerializer,
    TokenObtainPairWithoutPasswordSerializer,
    TokenObtainRefreshWithoutPasswordSerializer,
)

logger = logging.getLogger("watchtower-logger")


class CookerView(ModelViewSet):
    parser_classes = [MultiPartParser]
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

    def perform_create(self, serializer: BaseSerializer) -> None:
        try:
            super().perform_create(serializer)
        except IntegrityError as err:
            logger.error(err)
            return

        send_otp(serializer.validated_data.get("phone"))

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PATCH", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CookerCustomRendererWithData]

        return super().get_renderers()

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
            photo = (
                "cookers"
                + "/"
                + str(cooker.pk)
                + "/"
                + "profile_pics"
                + "/"
                + self.request.FILES["photo"].name
            )

        if photo is not None:
            upload_image_to_s3(self.request.FILES["photo"], photo)
            cooker.photo = photo
            cooker.save()

            if not old_photo_key.endswith("default-profile-pic.jpg"):
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
            activate_user(CookerModel, request.data)
            return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False)
    def auth(self, request) -> Response:
        phone = request.data.get("phone")

        if phone is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            cooker: CookerModel = CookerModel.objects.get(phone=e164_phone_format)
        except CookerModel.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not cooker.is_activated:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        otp_response: Union[dict, None] = send_otp(e164_phone_format)

        if otp_response is None:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        otp_response_status_code = (
            otp_response.get("MessageResponse", {})
            .get("Result", {})
            .get(e164_phone_format, {})
            .get("StatusCode")
        )

        if otp_response_status_code != status.HTTP_200_OK:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        otp_response_delivery_status = (
            otp_response.get("MessageResponse", {})
            .get("Result", {})
            .get(e164_phone_format, {})
            .get("DeliveryStatus")
        )

        if otp_response_delivery_status != "SUCCESSFUL":
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False, url_path="otp/ask")
    def ask_otp(self, request) -> Response:
        phone = request.data.get("phone")

        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        send_otp(e164_phone_format)

        return Response(status=status.HTTP_200_OK)


class DashboardView(GenericViewSet):
    permission_classes = [UserPermission]
    renderer_classes = [CustomJSONRendererWithData]

    def list(self, request) -> Response:
        start_date_str: Union[str, None] = request.query_params.get("start_date")
        end_date_str: Union[str, None] = request.query_params.get("end_date")

        if start_date_str is None or end_date_str is None:
            return Response(
                {
                    "ok": False,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }
            )

        try:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        except ValueError:
            return Response(
                {
                    "ok": False,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "error": "Invalid date format. ISO 8601 format is expected. Ex: 2024-01-01T00:00:00Z",
                }
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

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
                "data": orders_dict,
            }
        )


class DishView(ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DishPOSTSerializer

        if self.request.method == "PATCH":
            self.serializer_class = DishPATCHSerializer

        if self.request.method == "GET":
            self.serializer_class = DishGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CustomRendererWithData]

        return super().get_renderers()

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

    def list(self, request, *args, **kwargs) -> Response:
        request_name: Union[str, None] = self.request.query_params.get("name")
        request_category: Union[str, None] = self.request.query_params.get("category")
        request_status: Union[str, None] = self.request.query_params.get("is_enabled")

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_category is not None:
            self.queryset = self.queryset.filter(
                category__in=request_category.split(",")
            )

        if request_status is not None:
            self.queryset = self.queryset.filter(is_enabled=json.loads(request_status))

        self.queryset = self.queryset.filter(cooker__id=request.user.pk)

        if request_name is None and request_category is None and request_status is None:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        super().perform_destroy(instance)

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )


class DrinkView(ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DrinkModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DrinkPOSTSerializer

        if self.request.method == "PATCH":
            self.serializer_class = DrinkPATCHSerializer

        if self.request.method == "GET":
            self.serializer_class = DrinkGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CustomRendererWithData]

        return super().get_renderers()

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
        request_status: Union[str, None] = self.request.query_params.get("is_enabled")

        if request_name is not None:
            self.queryset = self.queryset.filter(name__icontains=request_name)

        if request_status is not None:
            self.queryset = self.queryset.filter(is_enabled=json.loads(request_status))

        if request_name is None and request_status is None:
            self.queryset = DrinkModel.objects.none()

        self.queryset = self.queryset.filter(cooker__id=request.user.pk)

        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        super().perform_destroy(instance)

        return Response(
            {
                "ok": True,
                "status_code": status.HTTP_200_OK,
            }
        )


class TokenObtainPairWithoutPasswordView(TokenViewBase):
    serializer_class = TokenObtainPairWithoutPasswordSerializer
    renderer_classes = [CustomRendererWithoutData]
    permission_classes = [CustomAPIKeyPermission]


class TokenObtainRefreshWithoutPasswordView(TokenViewBase):
    serializer_class = TokenObtainRefreshWithoutPasswordSerializer
    renderer_classes = [CustomRendererWithoutData]
