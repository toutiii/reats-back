import json
from typing import Union

from custom_renderers.renderers import (
    CookerCustomRendererWithData,
    CustomRendererWithData,
    CustomRendererWithoutData,
)
from django.db.models.query import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BaseRenderer
from rest_framework.serializers import BaseSerializer
from utils.common import upload_image_to_s3

from .models import CookerModel, DishModel
from .serializers import CookerSerializer, DishGETSerializer, DishPOSTSerializer


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
        if self.request.method == "POST":
            self.serializer_class = DishPOSTSerializer
        else:
            self.serializer_class = DishGETSerializer

        return super().get_serializer_class()

    def get_renderers(self) -> list[BaseRenderer]:
        if self.request.method == "POST":
            self.renderer_classes = [CustomRendererWithoutData]

        if self.request.method == "GET":
            self.renderer_classes = [CustomRendererWithData]

        return super().get_renderers()

    def perform_create(self, serializer) -> None:
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
        serializer.save()

    def get_queryset(self) -> QuerySet:
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
            return DishModel.objects.none()

        return self.queryset
