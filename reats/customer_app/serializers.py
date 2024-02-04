from cooker_app.models import DishModel
from rest_framework.serializers import ModelSerializer


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")
