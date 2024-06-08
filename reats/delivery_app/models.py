from django.core.validators import MinLengthValidator, RegexValidator
from django.db.models import (
    AutoField,
    BooleanField,
    CharField,
    FloatField,
    IntegerField,
    Manager,
)
from utils.models import ReatsModel


class DeliverModel(ReatsModel):

    DELIVERY_VEHICLE_CHOICES = [
        ("bike", "bike"),
        ("scooter", "scooter"),
        ("car", "car"),
    ]

    id: AutoField = AutoField(primary_key=True)
    firstname: CharField = CharField(max_length=100)
    lastname: CharField = CharField(max_length=100)
    phone: CharField = CharField(
        unique=True,
        max_length=17,
        validators=[MinLengthValidator(10)],
    )
    photo: CharField = CharField(
        max_length=512,
        default="delivers/1/profile_pics/default-profile-pic.jpg",
    )
    is_activated: BooleanField = BooleanField(default=False)
    delivery_vehicle: CharField = CharField(
        max_length=7,
        choices=DELIVERY_VEHICLE_CHOICES,
        default="bike",
    )
    town: CharField = CharField(max_length=100)
    delivery_radius: IntegerField = IntegerField()
    is_deleted: BooleanField = BooleanField(default=False)
    siret: CharField = CharField(
        unique=True,
        validators=[RegexValidator(regex=r"[0-9]{14}")],
        max_length=14,
    )
    is_online: BooleanField = BooleanField(default=False)
    grades: FloatField = FloatField(default=0.0)

    class Meta:
        db_table = "delivers"

    objects: Manager = Manager()  # For linting purposes
