from django.core.validators import MinLengthValidator
from django.db.models import (
    CASCADE,
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    IntegerField,
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
    is_enabled: BooleanField = BooleanField(default=True)

    class Meta:
        db_table = "addresses"

    def __str__(self):
        return (
            f"{self.street_number} {self.street_name}, {self.postal_code} {self.town}"
        )


class OrderModel(ReatsModel):
    STATUSES = [
        (
            "pending",
            "pending",
        ),  # Order has been paid, this is the initial state
        (
            "processing",
            "processing",
        ),  # State when the order has been accepted by the cooker
        (
            "completed",
            "completed",
        ),  # State when the order is ready for delivery
        (
            "cancelled_by_customer",
            "cancelled_by_customer",
        ),  # State when the order has been cancelled by the customer, this is a final state.
        (
            "cancelled_by_cooker",
            "cancelled_by_cooker",
        ),  # State when the order has been cancelled by the cooker, this is a final state.
        (
            "delivered",
            "delivered",
        ),  # State when the order has been delivered, this is a final state.
    ]
    id: AutoField = AutoField(primary_key=True)
    customer: ForeignKey = ForeignKey(
        CustomerModel,
        on_delete=CASCADE,
        related_name="orders",
    )
    address: ForeignKey = ForeignKey(
        AddressModel,
        on_delete=CASCADE,
        related_name="orders",
        null=True,
    )
    delivery_date: DateTimeField = DateTimeField()

    status: CharField = CharField(
        max_length=50,
        choices=STATUSES,
        default="pending",
    )

    class Meta:
        db_table = "orders"

    objects: Manager = Manager()  # For linting purposes


class OrderItemModel(ReatsModel):
    id: AutoField = AutoField(primary_key=True)
    order: ForeignKey = ForeignKey(
        OrderModel,
        on_delete=CASCADE,
        related_name="items",
    )
    dish: ForeignKey = ForeignKey(
        "cooker_app.DishModel",
        on_delete=CASCADE,
        null=True,
    )
    drink: ForeignKey = ForeignKey(
        "cooker_app.DrinkModel",
        on_delete=CASCADE,
        null=True,
    )
    dish_quantity: IntegerField = IntegerField(null=True)
    drink_quantity: IntegerField = IntegerField(null=True)

    class Meta:
        db_table = "order_items"

    objects: Manager = Manager()  # For linting purposes
