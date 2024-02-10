from django.core.validators import MinLengthValidator
from django.db.models import AutoField, BooleanField, CharField, Manager
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
