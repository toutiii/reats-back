from django.core.validators import MinLengthValidator
from django.db.models import (
    CASCADE,
    AutoField,
    BooleanField,
    CharField,
    ForeignKey,
    Manager,
)
from utils.models import ReatsModel


class CustomerModel(ReatsModel):
    id: AutoField = AutoField(primary_key=True)
    firstname: CharField = CharField(max_length=100)
    lastname: CharField = CharField(max_length=100)
    phone: CharField = CharField(
        unique=True, max_length=17, validators=[MinLengthValidator(10)]
    )
    photo: CharField = CharField(
        max_length=512,
        default="customers/1/profile_pics/default-profile-pic.jpg",
    )
    is_activated: BooleanField = BooleanField(default=False)

    class Meta:
        db_table = "customers"

    objects: Manager = Manager()  # For linting purposes


class AddressModel(ReatsModel):
    id: AutoField = AutoField(primary_key=True)
    street_name: CharField = CharField(max_length=100)
    street_number: CharField = CharField(max_length=10)
    town: CharField = CharField(max_length=100)
    postal_code: CharField = CharField(max_length=5)
    address_complement: CharField = CharField(max_length=512, null=True)
    customer: ForeignKey = ForeignKey(
        CustomerModel, on_delete=CASCADE, related_name="addresses"
    )

    class Meta:
        db_table = "addresses"

    def __str__(self):
        return (
            f"{self.street_number} {self.street_name}, {self.postal_code} {self.town}"
        )
