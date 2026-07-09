from core_app.models import DeliverFCMDeviceModel, DeliverModel
from django.conf import settings
from phonenumbers import PhoneNumberFormat, format_number, parse
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import format_phone, get_pre_signed_url


class DeliverSerializer(ModelSerializer):
    class Meta:
        model = DeliverModel
        exclude = ("photo", "is_deleted", "is_online", "is_activated")

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
        exclude = (
            "created",
            "modified",
            "grades",
            "is_activated",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["phone"] = format_number(parse(data["phone"], settings.PHONE_REGION), PhoneNumberFormat.NATIONAL).replace(
            " ", ""
        )
        data["photo"] = get_pre_signed_url(data["photo"])
        return data


class DeliverFCMDeviceSerializer(ModelSerializer):
    class Meta:
        model = DeliverFCMDeviceModel
        fields = ("token", "device_type")
