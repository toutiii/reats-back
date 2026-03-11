from datetime import datetime, timezone

from rest_framework import serializers
from rest_framework.serializers import CharField, ModelSerializer
from utils.common import get_pre_signed_url
from utils.enums import OrderStatusEnum

from .models import (
    AllergenDishModel,
    CookerModel,
    CustomerModel,
    DishImageModel,
    DishModel,
    DishRatingModel,
    DrinkModel,
    DrinkRatingModel,
    IngredientDishModel,
    NutritionalInfoDishModel,
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


class DishImageSerializer(ModelSerializer):
    url = serializers.SerializerMethodField()
    isPrimary = serializers.BooleanField(source="is_primary")

    class Meta:
        model = DishImageModel
        fields = ("id", "url", "isPrimary")

    def get_url(self, obj: DishImageModel) -> str | None:
        if obj.s3_key:
            return get_pre_signed_url(obj.s3_key)
        return None


class AllergenSerializer(ModelSerializer):
    class Meta:
        model = AllergenDishModel
        fields = ("id", "code", "name")


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = IngredientDishModel
        fields = ("id", "code", "name", "category")


class NutritionalInfoDishSerializer(ModelSerializer):
    class Meta:
        model = NutritionalInfoDishModel
        fields = ("calories", "protein", "carbs", "fat")


class DishGETSerializer(ModelSerializer):
    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    margin = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()

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
    preparation_time = serializers.IntegerField()
    max_concurrent_orders = serializers.IntegerField()
    current_orders = serializers.IntegerField(read_only=True)
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="created")
    updated_at = serializers.DateTimeField(source="modified")

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
            "is_enabled",
            "preparation_time",
            "max_concurrent_orders",
            "current_orders",
            "allergens",
            "ingredients",
            "created_at",
            "updated_at",
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
    current_orders = serializers.IntegerField(read_only=True)
    allergens = AllergenSerializer(many=True, read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)
    nutritional_info = NutritionalInfoDishSerializer(read_only=True)
    created_at = serializers.DateTimeField(source="created")
    updated_at = serializers.DateTimeField(source="modified")

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
            "is_enabled",
            "preparation_time",
            "max_concurrent_orders",
            "current_orders",
            "allergens",
            "ingredients",
            "nutritional_info" "created_at",
            "updated_at",
        )

    def get_margin(self, obj: DishModel) -> float | None:
        return obj.margin


class DishCustomerSerializer(AllergenIngredientMixin, ModelSerializer):
    """Serializer for customer-facing dish endpoints without sensitive financial data."""

    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()

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
