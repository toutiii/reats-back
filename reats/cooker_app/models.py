from django.core.validators import MinLengthValidator, RegexValidator
from django.db.models import (
    CASCADE,
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    IntegerField,
    Model,
    TextField,
)


class ReatsModel(Model):
    created: DateTimeField = DateTimeField(auto_now_add=True)
    modified: DateTimeField = DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CookerModel(ReatsModel):
    id: AutoField = AutoField(primary_key=True)
    firstname: CharField = CharField(max_length=100)
    lastname: CharField = CharField(max_length=100)
    phone: CharField = CharField(
        unique=True, max_length=17, validators=[MinLengthValidator(10)]
    )
    postal_code: CharField = CharField(
        max_length=5,
        validators=[RegexValidator(regex=r"[0-9]{5}")],
    )
    siret: CharField = CharField(
        unique=True,
        validators=[RegexValidator(regex=r"[0-9]{14}")],
        max_length=14,
    )
    street_name: CharField = CharField(max_length=100)
    street_number: CharField = CharField(max_length=10)
    town: CharField = CharField(max_length=100)
    address_complement: CharField = CharField(max_length=512)
    photo: CharField = CharField(max_length=512, null=True)
    max_order_number: IntegerField = IntegerField(default=10)

    class Meta:
        db_table = "cookers"


class DishModel(ReatsModel):
    CATEGORY_CHOICES = [
        ("starter", "starter"),
        ("dish", "dish"),
        ("dessert", "dessert"),
    ]

    id: AutoField = AutoField(primary_key=True)
    category: CharField = CharField(max_length=9, choices=CATEGORY_CHOICES)
    country: CharField = CharField(max_length=50)
    description: TextField = TextField(max_length=512, null=True)
    name: CharField = CharField(max_length=128)
    price: FloatField = FloatField()
    photo: CharField = CharField(max_length=512)
    cooker: ForeignKey = ForeignKey(CookerModel, on_delete=CASCADE)
    is_enabled: BooleanField = BooleanField(default=True)

    class Meta:
        db_table = "dishes"
