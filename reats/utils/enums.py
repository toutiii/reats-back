from enum import Enum


class OrderStatusEnum(str, Enum):
    DRAFT = "draft"  # Initial state for an order, a draft order has not been paid yet
    PENDING = (
        "pending"  # Order has been paid, waiting for the cooker acceptance or rejection
    )
    PROCESSING = "processing"  # State when the order has been accepted by the cooker
    COMPLETED = "completed"  # State when the order is ready for delivery
    CANCELLED_BY_CUSTOMER = "cancelled_by_customer"  # Final state when the order has been cancelled by the customer.
    CANCELLED_BY_COOKER = "cancelled_by_cooker"  # Final state when the order has been cancelled by the cooker.
    DELIVERED = (
        "delivered"  # State when the order has been delivered, this is a final state.
    )

    @classmethod
    def choices(cls):
        return [(key.value.lower(), key.name.lower()) for key in cls]
