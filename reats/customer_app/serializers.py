import ast
from datetime import datetime

import pytz
from cooker_app.models import DishModel, DrinkModel
from django.db import transaction
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import format_phone

from .models import AddressModel, CustomerModel, OrderItemModel, OrderModel


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
        exclude = ("is_enabled",)


class AddressGETSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("created", "modified", "is_enabled")


class DrinkGETSerializer(ModelSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("created", "modified")


class OrderItemGETSerializer(ModelSerializer):
    dish = DishGETSerializer()
    drink = DrinkGETSerializer()

    class Meta:
        model = OrderItemModel
        exclude = ("created", "modified", "order", "id")


class OrderGETSerializer(ModelSerializer):
    items = OrderItemGETSerializer(many=True)
    address = AddressGETSerializer()

    class Meta:
        model = OrderModel
        exclude = ("modified", "customer")
        many = True

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for item in data["items"]:
            if item["dish"] is None:
                item.pop("dish")
                item.pop("dish_quantity")
            if item["drink"] is None:
                item.pop("drink")
                item.pop("drink_quantity")

        return data


class OrderItemSerializer(ModelSerializer):
    class Meta:
        model = OrderItemModel
        exclude = ("created", "modified", "order", "id")


class OrderSerializer(ModelSerializer):
    items = OrderItemSerializer(many=True, required=True)

    class Meta:
        model = OrderModel
        exclude = (
            "created",
            "modified",
            "delivery_fees",
            "delivery_fees_bonus",
            "status",
        )

    def to_internal_value(self, data):
        # Modify the incoming data before validation
        data_to_validate: dict = {}
        data_to_validate["customer"] = data.get("customerID")
        data_to_validate["address"] = data.get("addressID")
        data_to_validate["delivery_planning"] = data.get("deliveryPlanning")

        # Dealing with delivery datetime
        if data.get("date") and data.get("time"):
            delivery_datetime_string = f"{data.get('date')} {data.get('time')}"
            delivery_datetime_object_naive = datetime.strptime(
                delivery_datetime_string, "%m/%d/%Y %H:%M:%S"
            )
            local_timezone = pytz.timezone("Europe/Paris")
            local_delivery_datetime = local_timezone.localize(
                delivery_datetime_object_naive
            )
            utc_delivery_datetime = local_delivery_datetime.astimezone(pytz.UTC)
            data_to_validate["scheduled_delivery_date"] = utc_delivery_datetime

        clean_order_items: list[dict] = []
        order_items = [
            ast.literal_eval(item)
            for item in self.context["request"].POST.getlist("items")
        ]

        for order_item in order_items[0]:
            temp_data: dict = {}
            try:
                temp_data["drink"] = order_item["drinkID"]
                temp_data["drink_quantity"] = order_item["drinkOrderedQuantity"]
            except KeyError:
                temp_data["drink"] = None
                temp_data["drink_quantity"] = None

            try:
                temp_data["dish"] = order_item["dishID"]
                temp_data["dish_quantity"] = order_item["dishOrderedQuantity"]
            except KeyError:
                temp_data["dish"] = None
                temp_data["dish_quantity"] = None

            clean_order_items.append(temp_data)

        data_to_validate["items"] = clean_order_items

        return super().to_internal_value(data_to_validate)

    def create(self, validated_data: dict):
        order_items_data = validated_data.pop("items")
        with transaction.atomic():
            order = OrderModel.objects.create(**validated_data)
            for item_data in order_items_data:
                OrderItemModel.objects.create(order=order, **item_data)
        return order


class OrderHistoryGETSerializer(ModelSerializer):
    items = OrderItemGETSerializer(many=True)
    address = AddressGETSerializer()
    order_amount = serializers.SerializerMethodField()

    def get_order_amount(self, instance):
        total = 0
        for item in instance.items.all():
            total += item.dish.price * item.dish_quantity if item.dish else 0
            total += item.drink.price * item.drink_quantity if item.drink else 0

        return total

    class Meta:
        model = OrderModel
        exclude = (
            "customer",
            "processing_date",
            "completed_date",
            "delivery_in_progress_date",
            "delivery_distance",
            "delivery_initial_distance",
        )
        many = True

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for item in data["items"]:
            if item["dish"] is None:
                item.pop("dish")
                item.pop("dish_quantity")
            if item["drink"] is None:
                item.pop("drink")
                item.pop("drink_quantity")

        return data


class DishCountriesGETSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishModel
        fields = ("country",)
