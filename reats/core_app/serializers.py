from datetime import datetime, timezone

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from utils.enums import OrderStatusEnum

from .models import DishModel, DrinkModel, OrderItemModel, OrderModel


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")


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


class OrderPATCHSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=True)

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
