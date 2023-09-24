import os

import boto3
from botocore.exceptions import ClientError
from custom_renderers.renderers import CustomRendererWithData, CustomRendererWithoutData
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import mixins, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BaseRenderer

from .models import CookerModel
from .serializers import CookerSerializer, DishSerializer

s3 = boto3.client("s3")


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


class DishView(viewsets.ModelViewSet):
    renderer_classes = [CustomRendererWithoutData]
    parser_classes = [MultiPartParser]
    serializer_class = DishSerializer

    def _upload_image_to_s3(
        self,
        request_data: dict,
        image: InMemoryUploadedFile,
    ) -> str:
        image_path = (
            "cookers"
            + "/"
            + str(request_data["cooker"])
            + "/"
            + "dishes"
            + "/"
            + request_data["category"]
            + "/"
            + image.name
        )

        try:
            s3.upload_fileobj(
                image,
                os.getenv("AWS_S3_BUCKET"),
                image_path,
            )
        except ClientError as err:
            print(err)

        image_base_url = f"https://{os.getenv('AWS_S3_BUCKET')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com"

        return image_base_url + "/" + image_path

    def create(self, request, *args, **kwargs):
        photo_url = self._upload_image_to_s3(
            request.data,
            request.FILES["photo"],
        )
        request.data._mutable = True
        request.data["photo"] = photo_url
        request.data._mutable = False

        return super().create(request, *args, **kwargs)
