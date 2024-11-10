from django.core.validators import MinLengthValidator
from django.db.models import (
    CASCADE,
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
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
    stripe_id: CharField = CharField(max_length=100, null=True)

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
        if self.address_complement:
            return f"{self.street_number} {self.street_name} {self.address_complement} {self.postal_code} {self.town}"

        return f"{self.street_number} {self.street_name} {self.postal_code} {self.town}"


class OrderModel(ReatsModel):
    class Meta:
        db_table = "orders"

    objects: Manager = Manager()  # For linting purposes

    STATUSES = [
        (
            "draft",
            "draft",
        ),  # Intial state for an order, a draft order has not been paid yet
        (
            "pending",
            "pending",
        ),  # Order has been paid, waiting for the cooker acceptance or rejection
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
    delivery_man: ForeignKey = ForeignKey(
        "delivery_app.DeliverModel",
        on_delete=CASCADE,
        null=True,
    )
    scheduled_delivery_date: DateTimeField = DateTimeField(null=True)
    is_scheduled: BooleanField = BooleanField(default=False)

    status: CharField = CharField(
        max_length=30,
        choices=STATUSES,
        default="draft",
    )
    processing_date: DateTimeField = DateTimeField(null=True)
    completed_date: DateTimeField = DateTimeField(null=True)
    delivery_in_progress_date: DateTimeField = DateTimeField(null=True)
    cancelled_date: DateTimeField = DateTimeField(null=True)
    delivered_date: DateTimeField = DateTimeField(null=True)

    delivery_fees: FloatField = FloatField(null=True)
    delivery_fees_bonus: FloatField = FloatField(null=True)
    delivery_distance: FloatField = FloatField(null=True)
    delivery_initial_distance: FloatField = FloatField(null=True)
    paid_date: DateTimeField = DateTimeField(null=True)
    stripe_payment_intent_id: CharField = CharField(max_length=100, null=True)
    stripe_payment_intent_secret: CharField = CharField(max_length=100, null=True)

    def get_state_map(self) -> dict:
        return {
            "draft": DraftState(),
            "pending": PendingState(),
            "processing": ProcessingState(),
            "completed": CompletedState(),
            "cancelled_by_customer": CancelledByCustomerState(),
            "cancelled_by_cooker": CancelledByCookerState(),
            "delivered": DeliveredState(),
        }

    def get_reverse_state_map(self) -> dict:
        return {
            "DraftState": "draft",
            "PendingState": "pending",
            "ProcessingState": "processing",
            "CompletedState": "completed",
            "CancelledByCustomerState": "cancelled_by_customer",
            "CancelledByCookerState": "cancelled_by_cooker",
            "DeliveredState": "delivered",
        }

    def get_state(self):
        return self.get_state_map().get(self.status, DraftState())

    def transition_to(self, new_status) -> None:
        current_state: OrderState = self.get_state()
        new_state: OrderState | None = self.get_state_map().get(new_status)

        if new_state:
            current_state.transition_to(self, new_state)


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


class OrderState:
    def can_transition_to(self, new_state):
        raise NotImplementedError("Subclasses must implement this method.")

    def transition_to(self, order: OrderModel, new_state):
        if self.can_transition_to(new_state):
            order.status = order.get_reverse_state_map().get(
                new_state.__class__.__name__
            )
            order.save()
        else:
            raise ValueError(
                f"Cannot transition from {self.__class__.__name__} to {new_state.__class__.__name__}"
            )


class DraftState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        return isinstance(new_state, PendingState)


class PendingState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        return (
            isinstance(new_state, ProcessingState)
            or isinstance(new_state, CancelledByCustomerState)
            or isinstance(new_state, CancelledByCookerState)
        )


class ProcessingState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        return isinstance(new_state, CompletedState) or isinstance(
            new_state, CancelledByCustomerState
        )


class CompletedState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        return isinstance(new_state, DeliveredState) or isinstance(
            new_state, CancelledByCustomerState
        )


class CancelledByCustomerState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        raise ValueError(
            "Cannot transition from CancelledByCustomerState to any other state."
        )


class CancelledByCookerState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        raise ValueError(
            "Cannot transition from CancelledByCookerState to any other state."
        )


class DeliveredState(OrderState):
    def can_transition_to(self, new_state: OrderState):
        raise ValueError("Cannot transition from DeliveredState to any other state.")
