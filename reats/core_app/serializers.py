from datetime import datetime, timezone

from rest_framework.serializers import CharField, ModelSerializer
from utils.enums import OrderStatusEnum

from .models import (
    DishModel,
    DrinkModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")


class DrinkGETSerializer(ModelSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("created", "modified")


class OrderDishItemGETSerializer(ModelSerializer):
    dish = DishGETSerializer()

    class Meta:
        model = OrderDishItemModel
        exclude = ("created", "modified", "order", "id")


class OrderDrinkItemGETSerializer(ModelSerializer):
    drink = DrinkGETSerializer()

    class Meta:
        model = OrderDrinkItemModel
        exclude = ("created", "modified", "order", "id")


class OrderPATCHSerializer(ModelSerializer):
    status = CharField(required=True)

    class Meta:
        model = OrderModel
        fields = ("status",)

    def update(self, instance: OrderModel, validated_data: dict):
        status = validated_data["status"]
        instance.status = status

        if status in (
            OrderStatusEnum.CANCELLED_BY_COOKER,
            OrderStatusEnum.CANCELLED_BY_CUSTOMER,
        ):
            instance.cancelled_date = datetime.now(timezone.utc)

        if status == OrderStatusEnum.PROCESSING:
            instance.processing_date = datetime.now(timezone.utc)

        if status == OrderStatusEnum.COMPLETED:
            instance.completed_date = datetime.now(timezone.utc)

        if status == OrderStatusEnum.DELIVERED:
            instance.delivered_date = datetime.now(timezone.utc)

        instance.save()

        return instance


class OrderRatingSerializer(ModelSerializer):
    class Meta:
        model = OrderModel
        fields = ("rating", "comment")

    def update(self, instance: OrderModel, validated_data: dict):
        instance.rating = validated_data.get("rating")
        instance.comment = validated_data.get("comment")
        instance.save()

        return instance
