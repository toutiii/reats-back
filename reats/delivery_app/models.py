from django.core.validators import MinLengthValidator
from django.db.models import AutoField, BooleanField, CharField, IntegerField, Manager
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
    delivery_vehicile: CharField = CharField(
        max_length=7,
        choices=DELIVERY_VEHICLE_CHOICES,
        default="bike",
    )
    max_capacity_per_delivery: IntegerField = IntegerField()
    delivery_postal_code: CharField = CharField(max_length=5)
    delivery_town: CharField = CharField(max_length=100)
    delivery_radius: IntegerField = IntegerField()
    is_enabled: BooleanField = BooleanField(default=True)

    class Meta:
        db_table = "delivers"

    objects: Manager = Manager()  # For linting purposes
