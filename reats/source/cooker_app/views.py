from rest_framework import mixins, viewsets
from source.custom_renderers.renderers import CustomRendererWithoutData

from .serializers import CookerSignUpSerializer, DishSerializer


class CookerSignUpView(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    renderer_classes = [CustomRendererWithoutData]
    serializer_class = CookerSignUpSerializer


class DishView(viewsets.ModelViewSet):
    renderer_classes = [CustomRendererWithoutData]
    serializer_class = DishSerializer
