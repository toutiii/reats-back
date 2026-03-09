from datetime import datetime, timezone
from utils.common import get_pre_signed_url

from rest_framework import serializers
from rest_framework.serializers import CharField, ModelSerializer
from utils.enums import OrderStatusEnum

from .models import (
    AllergenModel,
    CookerModel,
    CustomerModel,
    DishModel,
    DishRatingModel,
    DrinkModel,
    DrinkRatingModel,
    IngredientModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)


class AllergenIngredientMixin:
    """Mixin to avoid duplicating allergen/ingredient serialization logic."""

    def get_allergens(self, obj: DishModel) -> list[str]:
        return list(obj.allergens.values_list("code", flat=True))

    def get_ingredients(self, obj: DishModel) -> list[str]:
        return list(obj.ingredients.values_list("code", flat=True))



class DishRatingSerializer(ModelSerializer):
    class Meta:
        model = DishRatingModel
        fields = ("rating", "comment")


class DrinkRatingSerializer(ModelSerializer):
    class Meta:
        model = DrinkRatingModel
        fields = ("rating", "comment")


class SimpleCustomerSerializer(ModelSerializer):
    class Meta:
        model = CustomerModel
        fields = ("id", "firstname", "lastname", "stripe_id")


class SimpleCookerSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        fields = ("id", "firstname", "lastname", "email", "acceptance_rate")


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = IngredientModel
        fields = ("id", "code", "name")


class DishImageSerializer(ModelSerializer):
    # Stub for now, will be implemented in multi-photo PR
    url = serializers.SerializerMethodField()

    class Meta:
        model = DishModel  # Placeholder
        fields = ("id", "url")

    def get_url(self, obj):
        return ""


class NutritionalInfoSerializer(ModelSerializer):
    # Stub for now
    class Meta:
        model = DishModel # Placeholder
        fields = ("id",)


class AllergenSerializer(ModelSerializer):
    class Meta:
        model = AllergenModel
        fields = ("id", "code", "name")


class DishGETSerializer(ModelSerializer):
    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    margin = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()

    class Meta:
        model = DishModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
        )

    def get_margin(self, obj):
        return obj.margin

class DishListSerializer(AllergenIngredientMixin, ModelSerializer):
    margin = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_enabled")
    preparationTime = serializers.IntegerField(source="preparation_time")
    maxConcurrentOrders = serializers.IntegerField(source="max_concurrent_orders")
    currentOrders = serializers.IntegerField(source="current_orders", read_only=True)
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created")
    updatedAt = serializers.DateTimeField(source="modified")

    class Meta:
        model = DishModel
        fields = (
            "id",
            "name",
            "description",
            "price",
            "cost",
            "margin",
            "category",
            "image",
            "available",
            "preparationTime",
            "maxConcurrentOrders",
            "currentOrders",
            "allergens",
            "ingredients",
            "createdAt",
            "updatedAt",
        )

    def get_margin(self, obj: DishModel) -> float | None:
        return obj.margin

    def get_image(self, obj: DishModel) -> str | None:
        if obj.photo:
            return get_pre_signed_url(obj.photo)
        return None



class DishDetailSerializer(ModelSerializer):
    margin = serializers.SerializerMethodField()
    images = DishImageSerializer(many=True, read_only=True)
    available = serializers.BooleanField(source="is_enabled")
    preparationTime = serializers.IntegerField(source="preparation_time")
    maxConcurrentOrders = serializers.IntegerField(source="max_concurrent_orders")
    currentOrders = serializers.IntegerField(source="current_orders", read_only=True)
    allergens = AllergenSerializer(many=True, read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)
    nutritionalInfo = NutritionalInfoSerializer(source="nutritional_info", read_only=True)
    createdAt = serializers.DateTimeField(source="created")
    updatedAt = serializers.DateTimeField(source="modified")

    class Meta:
        model = DishModel
        fields = (
            "id",
            "name",
            "description",
            "price",
            "cost",
            "margin",
            "category",
            "images",
            "available",
            "preparationTime",
            "maxConcurrentOrders",
            "currentOrders",
            "allergens",
            "ingredients",
            "nutritionalInfo",
            "createdAt",
            "updatedAt",
        )

    def get_margin(self, obj: DishModel) -> float | None:
        return obj.margin



class DishCustomerSerializer(AllergenIngredientMixin, ModelSerializer):
    """Serializer for customer-facing dish endpoints without sensitive financial data."""

    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    allergens = serializers.SerializerMethodField()
    class Meta:
        model = DishModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
            "cost",  # Hide cost from customers
            "preparation_time",  # Internal operational data
            "max_concurrent_orders",  # Internal operational data
        )


class DishOrderHistorySerializer(ModelSerializer):
    """Serializer for dishes in order history - minimal fields."""

    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)

    class Meta:
        model = DishModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
            "cost",
            "preparation_time",
            "max_concurrent_orders",
            "allergens",
            "ingredients",
        )



class DrinkGETSerializer(ModelSerializer):
    ratings = DrinkRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)

    class Meta:
        model = DrinkModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
        )


class OrderDishItemGETSerializer(ModelSerializer):
    dish = DishGETSerializer()

    class Meta:
        model = OrderDishItemModel
        exclude = (
            "created",
            "modified",
            "order",
            "id",
        )


class OrderDishItemCustomerSerializer(ModelSerializer):
    """Customer-facing version using DishCustomerSerializer without margin."""

    dish = DishCustomerSerializer()

    class Meta:
        model = OrderDishItemModel
        exclude = (
            "created",
            "modified",
            "order",
            "id",
        )


class OrderDishItemHistorySerializer(ModelSerializer):
    """Order history version using DishOrderHistorySerializer."""

    dish = DishOrderHistorySerializer()

    class Meta:
        model = OrderDishItemModel
        exclude = (
            "created",
            "modified",
            "order",
            "id",
        )



class OrderDrinkItemGETSerializer(ModelSerializer):
    drink = DrinkGETSerializer()

    class Meta:
        model = OrderDrinkItemModel
        exclude = (
            "created",
            "modified",
            "order",
            "id",
        )


class OrderDrinkItemCustomerSerializer(ModelSerializer):
    """Customer-facing version for consistency."""

    drink = DrinkGETSerializer()

    class Meta:
        model = OrderDrinkItemModel
        exclude = (
            "created",
            "modified",
            "order",
            "id",
        )


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

        if status == OrderStatusEnum.IN_DELIVERY:
            instance.delivery_in_progress_date = datetime.now(timezone.utc)

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
