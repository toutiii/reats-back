import phonenumbers
from django.conf import settings
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import CookerModel, DishModel


class CookerSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        fields = "__all__"

    def validate_phone(self, phone):
        try:
            return phonenumbers.format_number(
                phonenumbers.parse(
                    phone,
                    settings.PHONE_REGION,
                ),
                phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            )
        except NumberParseException:
            raise serializers.ValidationError("Unparsable phone number")


class DishSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())

    class Meta:
        model = DishModel
        fields = "__all__"
