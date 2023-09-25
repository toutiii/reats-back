import boto3
from custom_renderers.renderers import CustomRendererWithData, CustomRendererWithoutData
from rest_framework import mixins, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BaseRenderer
from utils.common import upload_image_to_s3

from .models import CookerModel
from .serializers import CookerSerializer, DishSerializer


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
            self.renderer_classes = [CustomRendererWithData]

        return super().get_renderers()

    def perform_create(self, serializer) -> None:
        try:
            self.request.FILES["photo"]
        except KeyError:
            pass
        else:
            photo_url = upload_image_to_s3(
                self.request.FILES["photo"],
                "cookers"
                + "/"
                + serializer.validated_data["phone"]
                + "/"
                + "profile"
                + "/"
                + serializer.validated_data["firstname"],
            )
            serializer.validated_data["photo"] = photo_url

        super().perform_create(serializer)


class DishView(viewsets.ModelViewSet):
    renderer_classes = [CustomRendererWithoutData]
    parser_classes = [MultiPartParser]
    serializer_class = DishSerializer

    def perform_create(self, serializer) -> None:
        photo_url = upload_image_to_s3(
            self.request.FILES["photo"],
            "cookers"
            + "/"
            + str(serializer.validated_data["cooker"])
            + "/"
            + "dishes"
            + "/"
            + serializer.validated_data["category"]
            + "/"
            + self.request.FILES["photo"].name,
        )
        serializer.validated_data["photo"] = photo_url
        serializer.save()
