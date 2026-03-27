from decimal import Decimal
from typing import Any, Dict, Union

import phonenumbers
from core_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    DeliverModel,
    DishModel,
    DishNutritionalInfo,
    DrinkModel,
    DrinkNutritionalInfo,
    IngredientDishModel,
    IngredientDrinkModel,
    IngredientDrinkModel,
    OrderModel,
)
from core_app.serializers import (
    DishNutritionalInfoSerializer,
    DrinkNutritionalInfoSerializer,
    IngredientDrinkSerializer,
    IngredientDrinkSerializer,
    OrderDishItemGETSerializer,
    OrderDrinkItemGETSerializer,
)
from django.conf import settings
from django.db import transaction
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
            formatted_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.NATIONAL).replace(
                " ", ""
            )
        except NumberParseException:
            formatted_phone = data["phone"]

        return {
            "personal_infos_section": {
                "photo": get_pre_signed_url(data["photo"]),
                "siret": data["siret"],
                "firstname": data["firstname"],
                "lastname": data["lastname"],
                "phone": formatted_phone,
                "max_order_number": str(data["max_order_number"]),
                "is_online": data["is_online"],
                "acceptance_rate": data["acceptance_rate"],
                "email": data["email"],
            },
            "address_section": {
                "street_number": data.get("street_number"),
                "street_name": data.get("street_name"),
                "address_complement": data.get("address_complement"),
                "postal_code": data["postal_code"],
                "town": data["town"],
            },
        }


class DishSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())
    ingredients = serializers.JSONField(required=False, write_only=True)
    nutritional_info = serializers.JSONField(required=False, write_only=True, allow_null=True)

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        nutritional_data = validated_data.pop("nutritional_info", None)

        with transaction.atomic():
            dish = DishModel.objects.create(**validated_data)

            if ingredients_data:
                self._save_ingredients(dish, ingredients_data)

            if nutritional_data is not None:
                self._save_nutritional_info(dish, nutritional_data)

        return dish

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        nutritional_data = validated_data.pop("nutritional_info", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if ingredients_data is not None:
                self._save_ingredients(instance, ingredients_data)

            if nutritional_data is not None:
                self._save_nutritional_info(instance, nutritional_data)

        return instance

    def _save_nutritional_info(self, dish: DishModel, nutritional_data: dict) -> None:
        DishNutritionalInfo.objects.update_or_create(
            dish=dish,
            defaults=nutritional_data,
        )

    def _save_ingredients(self, dish: DishModel, ingredients_data: list[dict]) -> None:
        ingredient_objs: list[IngredientDishModel] = []
        for ing in ingredients_data:
            code = ing.get("code")
            if not code:
                continue

            defaults: dict = {
                "name": ing.get("name") or code.capitalize(),
                "category": ing.get("category"),
            }
            if "is_allergen" in ing:
                defaults["is_allergen"] = ing["is_allergen"]

            ingredient, created = IngredientDishModel.objects.get_or_create(
                code=code,
                defaults=defaults,
            )

            if not created:
                updated = False
                if ingredient.name != ing.get("name"):
                    ingredient.name = ing.get("name") or ingredient.name
                    updated = True
                if "category" in ing and ingredient.category != ing["category"]:
                    ingredient.category = ing["category"]
                    updated = True
                if "is_allergen" in ing and ingredient.is_allergen is not ing["is_allergen"]:
                    ingredient.is_allergen = ing["is_allergen"]
                    updated = True
                if updated:
                    ingredient.save()

            ingredient_objs.append(ingredient)

        dish.ingredients.set(ingredient_objs)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, "nutritional_info"):
            data["nutritional_info"] = DishNutritionalInfoSerializer(instance.nutritional_info).data
        else:
            data["nutritional_info"] = {}
        return data


class DishPOSTSerializer(DishSerializer):
    class Meta:
        model = DishModel
        exclude = ("is_enabled",)


class DishPATCHSerializer(DishSerializer):
    class Meta:
        model = DishModel
        fields = (
            "is_enabled",
            "cost",
            "preparation_time",
            "max_concurrent_orders",
            "name",
            "description",
            "price",
            "category",
            "ingredients",
            "nutritional_info",
        )


class DrinkSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())
    nutritional_info = serializers.JSONField(required=False, write_only=True, allow_null=True)
    ingredients = serializers.JSONField(required=False, write_only=True)
    ingredients = serializers.JSONField(required=False, write_only=True)

    def create(self, validated_data: dict) -> DrinkModel:
        nutritional_data = validated_data.pop("nutritional_info", None)
        ingredients_data = validated_data.pop("ingredients", None)

        with transaction.atomic():
            drink = DrinkModel.objects.create(**validated_data)

            if ingredients_data:
                self._save_ingredients(drink, ingredients_data)

            if nutritional_data is not None:
                self._save_nutritional_info(drink, nutritional_data)

        return drink

    def update(self, instance: DrinkModel, validated_data: dict) -> DrinkModel:
        nutritional_data = validated_data.pop("nutritional_info", None)
        ingredients_data = validated_data.pop("ingredients", None)
        ingredients_data = validated_data.pop("ingredients", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if ingredients_data is not None:
                self._save_ingredients(instance, ingredients_data)

            if ingredients_data is not None:
                self._save_ingredients(instance, ingredients_data)

            if nutritional_data is not None:
                self._save_nutritional_info(instance, nutritional_data)

        return instance

    def _save_nutritional_info(self, drink: DrinkModel, nutritional_data: dict) -> None:
        DrinkNutritionalInfo.objects.update_or_create(
            drink=drink,
            defaults=nutritional_data,
        )

    def _save_ingredients(self, drink: DrinkModel, ingredients_data: list[dict]) -> None:
        ingredient_objs: list[IngredientDrinkModel] = []
        for ing in ingredients_data:
            code = ing.get("code")
            if not code:
                continue

            defaults: dict = {
                "name": ing.get("name") or code.capitalize(),
            }
            if "category" in ing:
                defaults["category"] = ing["category"]
            if "is_allergen" in ing:
                defaults["is_allergen"] = ing["is_allergen"]

            ingredient, created = IngredientDrinkModel.objects.get_or_create(
                code=code,
                defaults=defaults,
            )

            if not created:
                updated = False
                if ingredient.name != ing.get("name"):
                    ingredient.name = ing.get("name") or ingredient.name
                    updated = True
                if "category" in ing and ingredient.category != ing["category"]:
                    ingredient.category = ing["category"]
                    updated = True
                if "is_allergen" in ing and ingredient.is_allergen != ing["is_allergen"]:
                    ingredient.is_allergen = ing["is_allergen"]
                    updated = True
                if updated:
                    ingredient.save()

            ingredient_objs.append(ingredient)

        drink.ingredients.set(ingredient_objs)

    def to_representation(self, instance: DrinkModel) -> dict:
        data = super().to_representation(instance)
        if hasattr(instance, "nutritional_info"):
            data["nutritional_info"] = DrinkNutritionalInfoSerializer(instance.nutritional_info).data
        else:
            data["nutritional_info"] = {}
        data["ingredients"] = IngredientDrinkSerializer(instance.ingredients.all(), many=True).data
        data["ingredients"] = IngredientDrinkSerializer(instance.ingredients.all(), many=True).data
        return data


class DrinkPOSTSerializer(DrinkSerializer):
    # Ingredients are mandatory at creation.
    ingredients = serializers.JSONField(required=True, write_only=True)

    class Meta:
        model = DrinkModel
        exclude = ("is_enabled",)


class DrinkPATCHSerializer(DrinkSerializer):
    class Meta:
        model = DrinkModel
        fields = (
            "is_enabled",
            "name",
            "description",
            "price",
            "capacity",
            "is_suitable_for_quick_delivery",
            "is_suitable_for_scheduled_delivery",
            "ingredients",
            "ingredients",
            "nutritional_info",
        )


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
            cooker_user: Union[CookerModel, None] = CookerModel.objects.get(phone=formatted_phone)
        except CookerModel.DoesNotExist:
            cooker_user = None

        try:
            customer_user: Union[CustomerModel, None] = CustomerModel.objects.get(phone=formatted_phone)

        except CustomerModel.DoesNotExist:
            customer_user = None

        try:
            deliver_user: Union[DeliverModel, None] = DeliverModel.objects.get(phone=formatted_phone)
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
            "email",
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
        data["total_amount"] = round(data["sub_total"] + data["service_fees"] + instance.delivery_fees, 2)

        return data


class RecentReviewSerializer(serializers.Serializer):
    """Serializer for recent reviews taking an Order model instance."""

    id = serializers.CharField()
    customer_name = serializers.SerializerMethodField()
    rating = serializers.IntegerField()
    comment = serializers.CharField(allow_null=True)
    date = serializers.DateTimeField(source="modified")
    order_number = serializers.SerializerMethodField()

    def get_customer_name(self, obj) -> str:
        if hasattr(obj, "customer"):
            customer = obj.customer
            first_name = customer.firstname
            last_name = customer.lastname
            if last_name:
                return f"{first_name} {last_name[0].upper()}."
            return first_name
        return "Unknown Customer"

    def get_order_number(self, obj) -> str:
        return f"#{obj.id}"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "id": data["id"],
            "customerName": data["customer_name"],
            "rating": data["rating"],
            "comment": data["comment"],
            "date": data["date"],
            "orderNumber": data["order_number"],
        }


class PopularItemSerializer(serializers.Serializer):
    """Serializer for popular items that handles transformation from QuerySet union."""

    item_id = serializers.UUIDField(source="id")
    item_name = serializers.CharField(source="name")
    total_sold = serializers.IntegerField(source="number_of_sold_items")
    item_price = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True)
    item_photo = serializers.CharField(allow_blank=True, allow_null=True, write_only=True)

    def to_representation(self, instance):
        """Transform QuerySet values dict to API response format."""
        revenue = Decimal(str(instance.get("item_price", 0))) * instance.get("total_sold", 0)
        photo = instance.get("item_photo")

        return {
            "id": str(instance["item_id"]),
            "name": instance["item_name"],
            "numberOfSoldItems": instance["total_sold"],
            "revenue": float(revenue),
            "image": get_pre_signed_url(photo) if photo else None,
        }


class IncomingChartSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    data = serializers.ListField(child=serializers.FloatField())  # type: ignore[assignment]


class StatsItemSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    trend = serializers.CharField(allow_null=True)


class RevenueStatsSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    currency = serializers.CharField()
    trend = serializers.CharField(allow_null=True)


class StatsSerializer(serializers.Serializer):
    active_orders = StatsItemSerializer()
    pending_orders = StatsItemSerializer()
    revenue = RevenueStatsSerializer()
    customers_served = StatsItemSerializer()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "activeOrders": data["active_orders"],
            "pendingOrders": data["pending_orders"],
            "revenue": data["revenue"],
            "customersServed": data["customers_served"],
        }


class DashboardStatsSerializer(serializers.Serializer):
    period = serializers.CharField()
    stats = StatsSerializer()
    revenue_chart = IncomingChartSerializer()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "period": data["period"],
            "stats": data["stats"],
            "revenueChart": data["revenue_chart"],
        }
