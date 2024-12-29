import ast
from datetime import datetime, timedelta

import pytz
from core_app.models import (
    AddressModel,
    CustomerModel,
    DishModel,
    OrderItemModel,
    OrderModel,
)
from core_app.serializers import OrderItemGETSerializer
from django.conf import settings
from django.db import transaction
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import compute_order_items_total_amount, format_phone


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


class AddressSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("is_enabled",)


class AddressGETSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("created", "modified", "is_enabled")


class OrderGETSerializer(ModelSerializer):
    items = OrderItemGETSerializer(many=True)
    address = AddressGETSerializer()

    class Meta:
        model = OrderModel
        exclude = ("modified", "customer")
        many = True

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["sub_total"] = compute_order_items_total_amount(instance)
        data["service_fees"] = round(data["sub_total"] * settings.SERVICE_FEES_RATE, 2)
        data["total_amount"] = round(
            data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2
        )

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
            "delivery_fees_bonus",
            "status",
        )

    def to_representation(self, instance: OrderModel):
        data = super().to_representation(instance)

        data["sub_total"] = compute_order_items_total_amount(instance)
        data["service_fees"] = round(data["sub_total"] * settings.SERVICE_FEES_RATE, 2)
        data["total_amount"] = round(
            data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2
        )

        return data

    def to_internal_value(self, data):
        # Modify the incoming data before validation
        data_to_validate = {}
        data_to_validate["customer"] = data.get("customerID")
        data_to_validate["address"] = data.get("addressID")
        data_to_validate["cooker"] = data.get("cookerID")

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

            # Check if utc_delivery_datetime is in the past and return a 400 response
            if utc_delivery_datetime < datetime.now(pytz.UTC):
                raise serializers.ValidationError(
                    {"date": "Scheduled delivery date must be in the future"},
                )

            # Check if utc_delivery_datetime is at least one hour in the future
            if utc_delivery_datetime < datetime.now(pytz.UTC) + timedelta(hours=1):
                raise serializers.ValidationError(
                    {
                        "date": "Scheduled delivery date must be at least one hour in the future"
                    },
                )

            data_to_validate["scheduled_delivery_date"] = utc_delivery_datetime

        clean_order_items = []
        order_items = [
            ast.literal_eval(item)
            for item in self.context["request"].POST.getlist("items")
        ]

        for order_item in order_items[0]:
            temp_data = {}
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

    def update(self, instance: OrderModel, validated_data: dict):
        order_items_data = validated_data.pop("items")
        with transaction.atomic():
            OrderItemModel.objects.filter(order=instance).delete()
            for item_data in order_items_data:
                OrderItemModel.objects.create(order=instance, **item_data)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        return instance


class DishCountriesGETSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishModel
        fields = ("country",)
