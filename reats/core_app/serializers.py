from datetime import datetime, timezone
from typing import Any, Union

from rest_framework import serializers
from rest_framework.serializers import CharField, ModelSerializer
from utils.common import get_pre_signed_url
from utils.enums import OrderStatusEnum

from .models import (
    CookerModel,
    CustomerModel,
    DishImageModel,
    DishModel,
    DishNutritionalInfo,
    DishRatingModel,
    DrinkImageModel,
    DrinkModel,
    DrinkRatingModel,
    IngredientDishModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)


class AllergenIngredientMixin:
    """Mixin to avoid duplicating allergen/ingredient serialization logic."""

    def get_allergens(self, obj: DishModel) -> list[str]:
        return list(obj.ingredients.filter(is_allergen=True).values_list("code", flat=True))

    def get_ingredients(self, obj: DishModel) -> list[str]:
        return list(obj.ingredients.values_list("code", flat=True))

    def get_image(self, obj: DishModel) -> str | None:
        """Returns the primary image URL for a dish."""
        primary = obj.images.filter(is_primary=True).first()  # type: ignore
        if primary:
            return get_pre_signed_url(primary.key)
        return None


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
        model = IngredientDishModel
        fields = ("id", "code", "name", "category", "is_allergen")


class DishImageSerializer(ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = DishImageModel
        fields = ("id", "url", "is_primary", "position")

    def get_url(self, obj: DishImageModel) -> str | None:
        return get_pre_signed_url(obj.key)


class DishGETSerializer(AllergenIngredientMixin, ModelSerializer):
    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    image = serializers.SerializerMethodField()
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


class NutritionalInfoMixin:
    """Mixin to avoid duplicating get_nutritional_info method."""

    def get_nutritional_info(self, obj: DishModel) -> dict:
        if hasattr(obj, "nutritional_info"):
            return DishNutritionalInfoSerializer(obj.nutritional_info).data
        return {}


class DishNutritionalInfoSerializer(ModelSerializer):
    class Meta:
        model = DishNutritionalInfo
        exclude = ("id", "dish")


class BaseDishSerializer(NutritionalInfoMixin, ModelSerializer):
    margin = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_enabled")
    current_orders = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(source="created")
    updated_at = serializers.DateTimeField(source="modified")

    nutritional_info = serializers.SerializerMethodField()

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
            "available",
            "is_enabled",
            "preparation_time",
            "max_concurrent_orders",
            "current_orders",
            "created_at",
            "updated_at",
            "nutritional_info",
        )

    def get_margin(self, obj: DishModel) -> float | None:
        return obj.margin


class DishListSerializer(AllergenIngredientMixin, BaseDishSerializer):
    image = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()

    class Meta(BaseDishSerializer.Meta):
        fields = BaseDishSerializer.Meta.fields + (  # type: ignore[assignment]
            "image",
            "allergens",
            "ingredients",
        )


class DishDetailSerializer(BaseDishSerializer):
    ingredients = IngredientSerializer(many=True, read_only=True)
    images = DishImageSerializer(many=True, read_only=True)
    allergens = serializers.SerializerMethodField()

    class Meta(BaseDishSerializer.Meta):
        fields = BaseDishSerializer.Meta.fields + (  # type: ignore[assignment]
            "allergens",
            "ingredients",
            "images",
        )

    def get_allergens(self, obj: DishModel) -> Any:
        allergens = obj.ingredients.filter(is_allergen=True)
        return IngredientSerializer(allergens, many=True).data


class DishCustomerSerializer(AllergenIngredientMixin, NutritionalInfoMixin, ModelSerializer):
    """Serializer for customer-facing dish endpoints without sensitive financial data."""

    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    nutritional_info = serializers.SerializerMethodField()

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


class DishOrderHistorySerializer(AllergenIngredientMixin, NutritionalInfoMixin, ModelSerializer):
    """Serializer for dishes in order history - minimal fields."""

    ratings = DishRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()
    nutritional_info = serializers.SerializerMethodField()

    class Meta:
        model = DishModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
            "cost",
            "preparation_time",
            "max_concurrent_orders",
        )


class DrinkImageSerializer(ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = DrinkImageModel
        fields = ("id", "url", "is_primary", "position")

    def get_url(self, obj: DrinkImageModel) -> Union[str, None]:
        return get_pre_signed_url(obj.key)


class BaseDrinkSerializer(ModelSerializer):
    ratings = DrinkRatingSerializer(many=True, read_only=True)
    cooker = SimpleCookerSerializer(read_only=True)

    class Meta:
        model = DrinkModel
        exclude = (
            "created",
            "modified",
            "is_deleted",
        )


class DrinkListSerializer(BaseDrinkSerializer):
    image = serializers.SerializerMethodField()

    class Meta(BaseDrinkSerializer.Meta):
        pass

    def get_image(self, obj: DrinkModel) -> Union[str, None]:
        primary = obj.images.filter(is_primary=True).first()  # type: ignore
        if primary:
            return get_pre_signed_url(primary.key)
        return None


class DrinkDetailSerializer(BaseDrinkSerializer):
    images = DrinkImageSerializer(many=True, read_only=True)

    class Meta(BaseDrinkSerializer.Meta):
        pass


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
    drink = DrinkListSerializer()

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

    drink = DrinkListSerializer()

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
