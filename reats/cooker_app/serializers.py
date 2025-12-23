from typing import Any, Dict, Union

import phonenumbers
from core_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    DeliverModel,
    DishModel,
    DrinkModel,
    OrderModel,
)
from core_app.serializers import OrderDishItemGETSerializer, OrderDrinkItemGETSerializer
from django.conf import settings
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from utils.common import (
    compute_order_items_total_amount,
    format_phone,
    get_pre_signed_url,
)


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

    def to_representation(self, instance: CookerModel) -> dict:
        data = super().to_representation(instance)

        try:
            parsed_phone = phonenumbers.parse(data["phone"], settings.PHONE_REGION)
            formatted_phone = phonenumbers.format_number(
                parsed_phone, phonenumbers.PhoneNumberFormat.NATIONAL
            ).replace(" ", "")
        except NumberParseException:
            formatted_phone = data["phone"]

        return {
            "personal_infos_section": {
                "title": "personal_infos",
                "data": {
                    "photo": get_pre_signed_url(data["photo"]),
                    "siret": data["siret"],
                    "firstname": data["firstname"],
                    "lastname": data["lastname"],
                    "phone": formatted_phone,
                    "max_order_number": str(data["max_order_number"]),
                    "is_online": data["is_online"],
                    "acceptance_rate": data["acceptance_rate"],
                },
            },
            "address_section": {
                "title": "address",
                "data": {
                    "street_number": data.get("street_number"),
                    "street_name": data.get("street_name"),
                    "address_complement": data.get("address_complement"),
                    "postal_code": data["postal_code"],
                    "town": data["town"],
                },
            },
        }


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


class TokenObtainPairWithoutPasswordSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = False
        self.fields["username"].required = False
        self.fields["phone"].required = True

    phone = serializers.CharField()

    def validate(self, attrs) -> dict:
        phone = attrs["phone"]
        request_headers = self.context.get("request").headers
        app_origin = request_headers.get("App-Origin")
        formatted_phone = format_phone(phone)

        if app_origin not in ["cooker", "customer", "delivery"]:
            raise ValidationError(f"Unknown App-Origin header value {app_origin}")

        try:
            cooker_user: Union[CookerModel, None] = CookerModel.objects.get(
                phone=formatted_phone
            )
        except CookerModel.DoesNotExist:
            cooker_user = None

        try:
            customer_user: Union[CustomerModel, None] = CustomerModel.objects.get(
                phone=formatted_phone
            )

        except CustomerModel.DoesNotExist:
            customer_user = None

        try:
            deliver_user: Union[DeliverModel, None] = DeliverModel.objects.get(
                phone=formatted_phone
            )
        except DeliverModel.DoesNotExist:
            deliver_user = None

        if cooker_user is None and customer_user is None and deliver_user is None:
            return {"ok": False, "status": status.HTTP_400_BAD_REQUEST}

        self.user: Union[CookerModel, CustomerModel, DeliverModel, None] = None

        if app_origin == "cooker":
            self.user = cooker_user
        elif app_origin == "customer":
            self.user = customer_user
        elif app_origin == "delivery":
            self.user = deliver_user
        else:
            self.user = None

        if self.user is None:
            return {"ok": False, "status": status.HTTP_400_BAD_REQUEST}

        refresh = self.get_token(self.user)
        data = {}
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return {"token": data, "user_id": self.user.pk}


class TokenObtainRefreshWithoutPasswordSerializer(TokenRefreshSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        return super().validate(attrs)


class CookerAddressSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        fields = (
            "id",
            "postal_code",
            "town",
        )


class CookerOrderCustomerGETSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        fields = (
            "id",
            "firstname",
            "lastname",
        )


class CookerOrderCookerGETSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        fields = (
            "id",
            "firstname",
            "lastname",
            "acceptance_rate",
        )


class CookerOrderGETSerializer(ModelSerializer):
    address = CookerAddressSerializer()
    dishes_items = OrderDishItemGETSerializer(many=True)
    drinks_items = OrderDrinkItemGETSerializer(many=True)
    customer = CookerOrderCustomerGETSerializer()
    cooker = CookerOrderCookerGETSerializer()

    class Meta:
        model = OrderModel
        exclude = (
            "modified",
            "stripe_payment_intent_id",
            "stripe_payment_intent_secret",
            "is_deleted",
        )
        many = True

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["sub_total"] = compute_order_items_total_amount(instance)
        data["service_fees"] = round(data["sub_total"] * settings.SERVICE_FEES_RATE, 2)
        data["total_amount"] = round(
            data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2
        )

        return data
