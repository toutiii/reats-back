from django.core.validators import MinLengthValidator, RegexValidator
from django.db.models import (
    CASCADE,
    AutoField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    Model,
    TextField,
)


class ReatsModel(Model):
    created = DateTimeField(auto_now_add=True)
    modified = DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CookerModel(ReatsModel):
    id = AutoField(primary_key=True)
    firstname = CharField(max_length=100)
    lastname = CharField(max_length=100)
    phone = CharField(unique=True, max_length=17, validators=[MinLengthValidator(10)])
    postal_code = CharField(
        max_length=5,
        validators=[RegexValidator(regex=r"[0-9]{5}")],
    )
    siret = CharField(
        unique=True,
        validators=[RegexValidator(regex=r"[0-9]{14}")],
        max_length=14,
    )
    street_name = CharField(max_length=100)
    street_number = CharField(max_length=10)
    town = CharField(max_length=100)
    address_complement = CharField(max_length=512)

    class Meta:
        db_table = "cookers"


class DishModel(ReatsModel):
    CATEGORY_CHOICES = [
        ("starter", "starter"),
        ("main_dish", "main_dish"),
        ("dessert", "dessert"),
    ]

    id = AutoField(primary_key=True)
    category = CharField(max_length=9, choices=CATEGORY_CHOICES)
    country = CharField(max_length=50)
    description = TextField(max_length=512, null=True)
    name = CharField(max_length=128)
    price = FloatField()
    photo = CharField(max_length=512)
    cooker = ForeignKey(CookerModel, on_delete=CASCADE)

    class Meta:
        db_table = "dishes"
