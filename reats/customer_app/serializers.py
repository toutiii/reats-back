from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core_app.models import (
    AddressModel,
    CustomerFCMDeviceModel,
    CustomerModel,
    DishModel,
    DishRatingModel,
    DrinkRatingModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from core_app.serializers import (
    OrderDishItemCustomerSerializer,
    OrderDrinkItemCustomerSerializer,
    SimpleCookerSerializer,
    SimpleCustomerSerializer,
)
from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.common import compute_order_items_total_amount, create_stripe_ephemeral_key, format_phone, get_pre_signed_url
from utils.enums import OrderStatusEnum


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Customer Inscription Example",
            value={
                "firstname": "Jean",
                "lastname": "Dupont",
                "phone": "+33612345678",
            },
            request_only=True,
        )
    ]
)
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Customer Profile Example",
            value={
                "id": 42,
                "firstname": "Jean",
                "lastname": "Dupont",
                "phone": "+33612345678",
                "photo": "customers/42/profile_pics/avatar.jpg",
                "is_activated": True,
                "stripe_id": "cus_abc123",
                "is_deleted": False,
            },
            response_only=True,
        )
    ]
)
class CustomerGETSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        exclude = ("created", "modified")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Customer Update Example",
            value={
                "firstname": "Jean",
                "lastname": "Martin",
                "phone": "+33612345678",
            },
            request_only=True,
        )
    ]
)
class CustomerPATCHSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        exclude = (
            "phone",
            "photo",
            "is_activated",
            "stripe_id",
            "is_deleted",
            "created",
            "modified",
        )

    def to_internal_value(self, data):
        allowed_fields = set(self.fields.keys())
        incoming_keys = set(data.keys())
        forbidden_keys = incoming_keys - allowed_fields

        if forbidden_keys:
            raise serializers.ValidationError(
                {field: ["Ce champ n'est pas autorisé dans cette requête."] for field in forbidden_keys}
            )

        return super().to_internal_value(data)


class AddressSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("is_enabled",)
        read_only_fields = ("customer",)


class FCMDeviceSerializer(ModelSerializer):
    class Meta:
        model = CustomerFCMDeviceModel
        fields = ("token", "device_type")


class AddressGETSerializer(ModelSerializer):
    class Meta:
        model = AddressModel
        exclude = ("created", "modified", "is_enabled")


class OrderGETSerializer(ModelSerializer):
    dishes_items = OrderDishItemCustomerSerializer(many=True)
    drinks_items = OrderDrinkItemCustomerSerializer(many=True)
    address = AddressGETSerializer()

    class Meta:
        model = OrderModel
        exclude = (
            "modified",
            "customer",
            "is_deleted",
        )
        many = True

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["sub_total"] = compute_order_items_total_amount(instance)
        data["service_fees"] = round(data["sub_total"] * settings.SERVICE_FEES_RATE, 2)
        data["total_amount"] = round(data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2)

        for item in data.get("drinks_items", []):
            if item["drink"].get("photo"):
                item["drink"]["photo"] = get_pre_signed_url(item["drink"]["photo"])

        order_status = data.get("status")

        if order_status is None or order_status == OrderStatusEnum.DRAFT:
            customer = instance.customer
            data["ephemeral_key"] = create_stripe_ephemeral_key(customer)

        if instance.cooker:
            cooker = instance.cooker
            data["cooker"] = SimpleCookerSerializer(cooker).data

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
            "is_deleted",
        )
        read_only_fields = ("delivery_fees", "status")

    def to_representation(self, instance: OrderModel):
        data = super().to_representation(instance)

        data["sub_total"] = compute_order_items_total_amount(instance)
        data["service_fees"] = round(data["sub_total"] * settings.SERVICE_FEES_RATE, 2)
        data["total_amount"] = round(data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2)

        if instance.cooker:
            data["cooker"] = SimpleCookerSerializer(instance.cooker).data

        if instance.customer:
            data["customer"] = SimpleCustomerSerializer(instance.customer).data

        if instance.status == OrderStatusEnum.DRAFT:
            data["ephemeral_key"] = create_stripe_ephemeral_key(instance.customer)
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
            delivery_datetime_object_naive = datetime.strptime(delivery_datetime_string, "%m/%d/%Y %H:%M:%S")
            local_timezone = ZoneInfo("Europe/Paris")
            local_delivery_datetime = delivery_datetime_object_naive.replace(tzinfo=local_timezone)
            utc_delivery_datetime = local_delivery_datetime.astimezone(timezone.utc)

            # Check if utc_delivery_datetime is in the past and return a 400 response
            if utc_delivery_datetime < datetime.now(timezone.utc):
                raise serializers.ValidationError(
                    {"date": "Scheduled delivery date must be in the future"},
                )

            # Check if utc_delivery_datetime is at least one hour in the future
            if utc_delivery_datetime < datetime.now(timezone.utc) + timedelta(hours=1):
                raise serializers.ValidationError(
                    {"date": "Scheduled delivery date must be at least one hour in the future"},
                )

            data_to_validate["scheduled_delivery_date"] = utc_delivery_datetime

        # The endpoint only accepts JSON, so dishes_items / drinks_items already
        # arrive as lists of dicts. We just remap the client field names to the
        # nested model fields expected by the serializer.
        data_to_validate["dishes_items"] = [
            {"dish": item["dishID"], "dish_quantity": item["dishOrderedQuantity"]}
            for item in data.get("dishes_items", [])
        ]

        data_to_validate["drinks_items"] = [
            {"drink": item["drinkID"], "drink_quantity": item["drinkOrderedQuantity"]}
            for item in data.get("drinks_items", [])
        ]

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
        child=serializers.FloatField(min_value=0.0, max_value=5.0),
        required=True,
    )
    comments = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )

    def validate(self, attrs):
        dishes_ids = attrs.get("dishes_ids")
        ratings = attrs.get("ratings")
        comments = attrs.get("comments", [])

        if len(dishes_ids) != len(ratings):
            raise serializers.ValidationError("The number of dishes_ids and ratings must match.")
        if comments and len(dishes_ids) != len(comments):
            raise serializers.ValidationError("The number of dishes_ids and comments must match.")
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
        child=serializers.FloatField(min_value=0.0, max_value=5.0),
        required=True,
    )
    comments = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )

    def validate(self, attrs):
        drink_ids = attrs.get("drink_ids")
        ratings = attrs.get("ratings")
        comments = attrs.get("comments", [])

        if len(drink_ids) != len(ratings):
            raise serializers.ValidationError("The number of drink_ids and ratings must match.")
        if comments and len(drink_ids) != len(comments):
            raise serializers.ValidationError("The number of drink_ids and comments must match.")
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
