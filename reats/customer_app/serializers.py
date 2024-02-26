from cooker_app.models import DishModel
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import format_phone

from .models import AddressModel, CustomerModel


class CustomerSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        exclude = ("photo",)

    def validate_phone(self, phone):
        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            raise serializers.ValidationError("Unparsable phone number")
        else:
            return e164_phone_format


class CustomerGETSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        exclude = ("created", "modified")


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")


class AddressSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        fields = "__all__"


class AddressGETSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("created", "modified")
