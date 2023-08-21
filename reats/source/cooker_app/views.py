from rest_framework import mixins, viewsets
from source.custom_renderers.renderers import CustomRendererWithoutData

from .serializers import CookerSignUpSerializer


class CookerSignUpView(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    renderer_classes = [CustomRendererWithoutData]
    serializer_class = CookerSignUpSerializer
