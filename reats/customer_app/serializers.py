import ast
from datetime import datetime, timedelta

import pytz
from core_app.models import (
    AddressModel,
    CustomerModel,
    DishModel,
    DishRatingModel,
    DrinkRatingModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from core_app.serializers import OrderDishItemGETSerializer, OrderDrinkItemGETSerializer
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
    dishes_items = OrderDishItemGETSerializer(many=True)
    drinks_items = OrderDrinkItemGETSerializer(many=True)
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

        return data


class OrderDishItemSerializer(ModelSerializer):
    class Meta:
        model = OrderDishItemModel
        exclude = ("created", "modified", "order", "id")


class OrderDrinkItemSerializer(ModelSerializer):
    class Meta:
        model = OrderDrinkItemModel
        exclude = ("created", "modified", "order", "id")


class OrderSerializer(ModelSerializer):
    dishes_items = OrderDishItemSerializer(many=True, required=True)
    drinks_items = OrderDrinkItemSerializer(many=True, required=False)

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

        # We extract the dishes items from the request
        clean_order_dishes_items = []
        dishes_order_items = [
            ast.literal_eval(item)
            for item in self.context["request"].POST.getlist("dishes_items")
        ]  # This will return a list of list
        for dish_order_item in dishes_order_items[0]:
            temp_data = {}
            temp_data["dish"] = dish_order_item["dishID"]
            temp_data["dish_quantity"] = dish_order_item["dishOrderedQuantity"]
            clean_order_dishes_items.append(temp_data)

        data_to_validate["dishes_items"] = clean_order_dishes_items

        # Then we extract the drinks items from the request
        clean_order_drinks_items = []
        drinks_order_items = [
            ast.literal_eval(item)
            for item in self.context["request"].POST.getlist("drinks_items")
        ]  # This will return a list of list

        for drink_order_item in drinks_order_items[0]:
            temp_data = {}
            temp_data["drink"] = drink_order_item["drinkID"]
            temp_data["drink_quantity"] = drink_order_item["drinkOrderedQuantity"]
            clean_order_drinks_items.append(temp_data)

        data_to_validate["drinks_items"] = clean_order_drinks_items

        return super().to_internal_value(data_to_validate)

    def create(self, validated_data: dict):
        order_dishes_items_data = validated_data.pop("dishes_items")
        order_drinks_items_data = validated_data.pop("drinks_items")

        with transaction.atomic():
            order = OrderModel.objects.create(**validated_data)

            for dish_item_data in order_dishes_items_data:
                OrderDishItemModel.objects.create(order=order, **dish_item_data)

            for drink_item_data in order_drinks_items_data:
                OrderDrinkItemModel.objects.create(order=order, **drink_item_data)

        return order

    def update(self, instance: OrderModel, validated_data: dict):
        order_dishes_items_data = validated_data.pop("dishes_items")
        order_drinks_items_data = validated_data.pop("drinks_items")

        OrderDishItemModel.objects.filter(order=instance).delete()
        OrderDrinkItemModel.objects.filter(order=instance).delete()

        with transaction.atomic():

            for dish_item_data in order_dishes_items_data:
                OrderDishItemModel.objects.create(order=instance, **dish_item_data)

            for drink_item_data in order_drinks_items_data:
                OrderDrinkItemModel.objects.create(order=instance, **drink_item_data)

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        return instance


class DishCountriesGETSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishModel
        fields = ("country",)


class BulkDishRatingSerializer(serializers.Serializer):
    """Serializer for handling bulk dish ratings creation"""

    dishes_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
    )
    ratings = serializers.ListField(
        child=serializers.FloatField(),
        required=True,
    )
    comments = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )
    customer_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        dishes_ids = attrs.get("dishes_ids")
        ratings = attrs.get("ratings")
        comments = attrs.get("comments", [])

        if len(dishes_ids) != len(ratings):
            raise serializers.ValidationError(
                "The number of dishes_ids and ratings must match."
            )
        if comments and len(dishes_ids) != len(comments):
            raise serializers.ValidationError(
                "The number of dishes_ids and comments must match."
            )
        return attrs

    def create(self, validated_data):
        dishes_ids = validated_data["dishes_ids"]
        ratings = validated_data["ratings"]
        comments = validated_data.get("comments", [])
        customer_id = validated_data["customer_id"]

        dish_ratings = []
        for idx, dish_id in enumerate(dishes_ids):
            dish_ratings.append(
                DishRatingModel(
                    dish_id=dish_id,
                    rating=ratings[idx],
                    comment=comments[idx] if comments else None,
                    customer_id=customer_id,
                )
            )

        # Bulk create all dish ratings
        return DishRatingModel.objects.bulk_create(dish_ratings)


class BulkDrinkRatingSerializer(serializers.Serializer):
    """Serializer for handling bulk drink ratings creation."""

    drink_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
    )
    ratings = serializers.ListField(
        child=serializers.FloatField(),
        required=True,
    )
    comments = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )
    customer_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        drink_ids = attrs.get("drink_ids")
        ratings = attrs.get("ratings")
        comments = attrs.get("comments", [])

        if len(drink_ids) != len(ratings):
            raise serializers.ValidationError(
                "The number of drink_ids and ratings must match."
            )
        if comments and len(drink_ids) != len(comments):
            raise serializers.ValidationError(
                "The number of drink_ids and comments must match."
            )
        return attrs

    def create(self, validated_data):
        drink_ids = validated_data["drink_ids"]
        ratings = validated_data["ratings"]
        comments = validated_data.get("comments", [])
        customer_id = validated_data["customer_id"]

        drink_ratings = []
        for idx, drink_id in enumerate(drink_ids):
            drink_ratings.append(
                DrinkRatingModel(
                    drink_id=drink_id,
                    rating=ratings[idx],
                    comment=comments[idx] if comments else None,
                    customer_id=customer_id,
                )
            )

        # Bulk create all drink ratings
        return DrinkRatingModel.objects.bulk_create(drink_ratings)
