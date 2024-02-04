from typing import Union

from cooker_app.models import DishModel
from custom_renderers.renderers import CustomRendererWithData
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .serializers import DishGETSerializer


class DishView(ListModelMixin, GenericViewSet):
    serializer_class = DishGETSerializer
    renderer_classes = [CustomRendererWithData]
    parser_classes = [MultiPartParser]
    queryset = DishModel.objects.all()

    def list(self, request, *args, **kwargs) -> Response:
        request_sort: Union[str, None] = self.request.query_params.get("sort")

        if request_sort is not None:
            if request_sort == "new":
                self.queryset = self.queryset.order_by("created")
            else:
                self.queryset = self.queryset.order_by("created")
        else:
            self.queryset = DishModel.objects.none()

        return super().list(request, *args, **kwargs)
