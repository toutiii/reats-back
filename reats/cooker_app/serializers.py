from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers, status
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from utils.common import format_phone

from .models import CookerModel, DishModel, DrinkModel


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


class DishGETSerializer(ModelSerializer):
    class Meta:
        model = DishModel
        exclude = ("created", "modified")


class DishSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())


class DishPOSTSerializer(DishSerializer):
    class Meta:
        model = DishModel
        exclude = ("photo", "is_enabled")


class DishPATCHSerializer(DishSerializer):
    class Meta:
        model = DishModel
        fields = ("is_enabled",)


class DrinkGETSerializer(ModelSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("created", "modified")


class DrinkSerializer(ModelSerializer):
    cooker = serializers.PrimaryKeyRelatedField(queryset=CookerModel.objects.all())


class DrinkPOSTSerializer(DrinkSerializer):
    class Meta:
        model = DrinkModel
        exclude = ("photo", "is_enabled")


class DrinkPATCHSerializer(DrinkSerializer):
    class Meta:
        model = DrinkModel
        fields = ("is_enabled",)


class TokenObtainPairWithoutPasswordSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = False

    phone = serializers.CharField()

    def validate(self, attrs) -> dict:
        try:
            self.user: CookerModel = CookerModel.objects.get(
                phone=format_phone(self.initial_data["phone"])
            )
        except CookerModel.DoesNotExist:
            return {"ok": False, "status": status.HTTP_400_BAD_REQUEST}

        refresh = self.get_token(self.user)

        data = {}
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return {"ok": True, "token": data, "user_id": self.user.pk}
