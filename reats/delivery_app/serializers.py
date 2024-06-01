from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import format_phone

from .models import DeliverModel


class DeliverSerializer(ModelSerializer):
    class Meta:
        model = DeliverModel
        exclude = ("photo", "is_enabled")

    def validate_phone(self, phone):
        try:
            e164_phone_format = format_phone(phone)
        except NumberParseException:
            raise serializers.ValidationError("Unparsable phone number")
        else:
            return e164_phone_format


class DeliverGETSerializer(ModelSerializer):
    class Meta:
        model = DeliverModel
        exclude = ("created", "modified")
