import json
from typing import Union

from custom_renderers.renderers import (
    CookerCustomRendererWithData,
    CustomRendererWithData,
    CustomRendererWithoutData,
)
from rest_framework import mixins, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from utils.common import delete_s3_object, upload_image_to_s3

from .models import CookerModel, DishModel
from .serializers import (
    CookerSerializer,
    DishGETSerializer,
    DishPATCHSerializer,
    DishPOSTSerializer,
)


class CookerView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CookerSerializer
    queryset = CookerModel.objects.all()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method == "POST":
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CookerCustomRendererWithData]

        return super().get_renderers()

    def perform_create(self, serializer) -> None:
        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            photo = (
                "cookers"
                + "/"
                + serializer.validated_data["phone"]
                + "/"
                + "profile"
                + "/"
                + self.request.FILES["photo"].name
            )

            upload_image_to_s3(self.request.FILES["photo"], photo)
            serializer.validated_data["photo"] = photo

        super().perform_create(serializer)


class DishView(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.request.method in ("POST", "PUT"):
            self.serializer_class = DishPOSTSerializer
        elif self.request.method == "PATCH":
            self.serializer_class = DishPATCHSerializer
        else:
            self.serializer_class = DishGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method in ("POST", "PUT", "PATCH"):
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

        if request_name is None and request_category is None and request_status is None:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)
