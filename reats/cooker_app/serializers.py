from decimal import Decimal
from typing import Any, Dict, Union, cast

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
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from core_app.serializers import (
    DishNutritionalInfoSerializer,
    DrinkNutritionalInfoSerializer,
    IngredientDrinkSerializer,
    OrderDishItemGETSerializer,
    OrderDrinkItemGETSerializer,
)
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, Token
from rest_framework_simplejwt.utils import datetime_from_epoch
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


class CookerPATCHSerializer(ModelSerializer):
    class Meta:
        model = CookerModel
        exclude = (
            "phone",
            "photo",
            "is_activated",
            "acceptance_rate",
            "last_acceptance_rate_update_date",
            "is_deleted",
            "created",
            "modified",
        )

    def to_internal_value(self, data):
        allowed_fields = set(self.fields.keys())
        incoming_keys = set(data.keys())
        forbidden_keys = incoming_keys - allowed_fields

        if forbidden_keys:
            raise ValidationError(
                {field: ["Ce champ n'est pas autorisé dans cette requête."] for field in forbidden_keys}
            )

        return super().to_internal_value(data)


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
    photos = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
        help_text="One or more dish images. Handled via request.FILES in the view.",
    )

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()  # make QueryDict mutable
        data.pop("photos", None)
        data.pop("photos[]", None)
        return super().to_internal_value(data)

    def create(self, validated_data):
        validated_data.pop("photos", None)
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
            "photos",
        )


class DrinkSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())
    nutritional_info = serializers.JSONField(required=False, write_only=True, allow_null=True)
    ingredients = serializers.JSONField(required=False, write_only=True)
    photos = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
        help_text="One or more drink images. Handled via request.FILES in the view.",
    )

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()  # make QueryDict mutable
        data.pop("photos", None)
        data.pop("photos[]", None)
        return super().to_internal_value(data)

    def create(self, validated_data: dict) -> DrinkModel:
        validated_data.pop("photos", None)
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
        validated_data.pop("photos", None)
        nutritional_data = validated_data.pop("nutritional_info", None)
        ingredients_data = validated_data.pop("ingredients", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

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
            "cost",
            "capacity",
            "is_suitable_for_quick_delivery",
            "is_suitable_for_scheduled_delivery",
            "ingredients",
            "nutritional_info",
        )


class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = Token.for_user.__func__(cls, user)

        if "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS:
            jti = token[api_settings.JTI_CLAIM]
            exp = token["exp"]

            OutstandingToken.objects.create(
                user=None,
                jti=jti,
                token=str(token),
                created_at=token.current_time,
                expires_at=datetime_from_epoch(exp),
            )

        return token


class TokenObtainPairWithoutPasswordSerializer(TokenObtainPairSerializer):
    token_class = CustomRefreshToken

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = False
        self.fields["username"].required = False
        self.fields["phone"].required = True

    phone = serializers.CharField()

    def validate(self, attrs) -> dict:
        phone = attrs["phone"]
        request_headers = self.context["request"].headers
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

        refresh = cast(CustomRefreshToken, self.get_token(cast(AbstractBaseUser, self.user)))
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


class BaseCookerOrderItemSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()

    def get_item(self, obj):
        return getattr(obj, "dish", None) or getattr(obj, "drink", None)

    def get_id(self, obj) -> Union[int, None]:
        item = self.get_item(obj)
        return item.id if item else None

    def get_name(self, obj) -> str:
        item = self.get_item(obj)
        return item.name if item else ""

    def get_quantity(self, obj) -> Union[int, None]:
        return getattr(obj, "dish_quantity", None) or getattr(obj, "drink_quantity", None)

    def get_unit_price(self, obj) -> float:
        item = self.get_item(obj)
        return item.price if item else 0.0

    def get_image(self, obj) -> Union[str, None]:
        item = self.get_item(obj)
        if not item or not hasattr(item, "images"):
            return None
        primary = item.images.filter(is_primary=True).first()
        if primary:
            return get_pre_signed_url(primary.key)
        return None


class CookerOrderListDishSerializer(BaseCookerOrderItemSerializer):
    category = serializers.CharField(source="dish.category")

    class Meta:
        model = OrderDishItemModel
        fields = (
            "id",
            "name",
            "category",
            "image",
            "quantity",
            "unit_price",
        )


class CookerOrderListDrinkSerializer(BaseCookerOrderItemSerializer):
    capacity = serializers.SerializerMethodField()

    class Meta:
        model = OrderDrinkItemModel
        fields = (
            "id",
            "name",
            "capacity",
            "image",
            "quantity",
            "unit_price",
        )

    def get_capacity(self, obj: OrderDrinkItemModel) -> str:
        if not obj.drink:
            return ""
        unit_map = {"liter": "L", "centiliters": "cl"}
        unit_suffix = unit_map.get(obj.drink.unit, obj.drink.unit)
        return f"{obj.drink.capacity}{unit_suffix}"


class CookerOrderListSerializer(serializers.ModelSerializer):
    customer = CookerOrderCustomerGETSerializer()
    address = CookerAddressSerializer()
    dishes_items = CookerOrderListDishSerializer(many=True)
    drinks_items = CookerOrderListDrinkSerializer(many=True)
    items_count = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    service_fees = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderModel
        fields = (
            "id",
            "status",
            "created",
            "customer",
            "address",
            "dishes_items",
            "drinks_items",
            "items_count",
            "sub_total",
            "delivery_fees",
            "service_fees",
            "total_amount",
        )

    def get_items_count(self, obj: OrderModel) -> int:
        return obj.dishes_items.count() + obj.drinks_items.count()  # ty: ignore[unresolved-attribute]

    def get_sub_total(self, obj: OrderModel) -> float:
        return compute_order_items_total_amount(obj)

    def get_service_fees(self, obj: OrderModel) -> float:
        sub_total = compute_order_items_total_amount(obj)
        return round(sub_total * settings.SERVICE_FEES_RATE, 2)

    def get_total_amount(self, obj: OrderModel) -> float:
        sub_total = compute_order_items_total_amount(obj)
        service_fees = round(sub_total * settings.SERVICE_FEES_RATE, 2)
        return round(sub_total + service_fees + (obj.delivery_fees or 0), 2)


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

        data["items_count"] = instance.dishes_items.count() + instance.drinks_items.count()
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
