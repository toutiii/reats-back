from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import format_phone

from .models import CookerModel, DishModel, DrinkModel


class CookerSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        exclude = ("photo",)

    def validate_phone(self, phone):
        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            raise serializers.ValidationError("Unparsable phone number")
        else:
            return e164_phone_format


class CookerGETSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        exclude = ("created", "modified")


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")


class DishSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())


class DishPOSTSerializer(DishSerializer):
    class Meta:
        model = DishModel
        exclude = ("photo", "is_enabled")


class DishPATCHSerializer(DishSerializer):
    class Meta:
        model = DishModel
        fields = ("is_enabled",)


class DrinkGETSerializer(ModelSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("created", "modified")


class DrinkSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())


class DrinkPOSTSerializer(DrinkSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("photo", "is_enabled")


class DrinkPATCHSerializer(DrinkSerializer):
    class Meta:
        model = DrinkModel
        fields = ("is_enabled",)
