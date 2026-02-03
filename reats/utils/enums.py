from enum import Enum

from django.utils.translation import gettext_lazy as _


class OrderStatusEnum(str, Enum):
    DRAFT = "draft"  # Initial state for an order, a draft order has not been paid yet
    PENDING = "pending"  # Order has been paid, waiting for the cooker acceptance or rejection
    PROCESSING = "processing"  # State when the order has been accepted by the cooker
    COMPLETED = "completed"  # State when the order is ready for delivery
    IN_DELIVERY = "in_delivery"  # State when the order is on its way to the customer
    CANCELLED_BY_CUSTOMER = "cancelled_by_customer"  # Final state when the order has been cancelled by the customer.
    CANCELLED_BY_COOKER = "cancelled_by_cooker"  # Final state when the order has been cancelled by the cooker.
    DELIVERED = "delivered"  # State when the order has been delivered, this is a final state.

    @classmethod
    def choices(cls):
        return [(key.value.lower(), key.name.lower()) for key in cls]


class TimeFrameEnum(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class TodayChartLabelEnum(str, Enum):
    H00_04 = "00h-04h"
    H04_08 = "04h-08h"
    H08_12 = "08h-12h"
    H12_16 = "12h-16h"
    H16_20 = "16h-20h"
    H20_24 = "20h-24h"


class WeekChartLabelEnum(str, Enum):
    MON = "Mon"
    TUE = "Tue"
    WED = "Wed"
    THU = "Thu"
    FRI = "Fri"
    SAT = "Sat"
    SUN = "Sun"


class MonthChartLabelEnum(str, Enum):
    WEEK_1 = "Week 1"
    WEEK_2 = "Week 2"
    WEEK_3 = "Week 3"
    WEEK_4 = "Week 4"


class YearChartLabelEnum(str, Enum):
    JAN = "Jan"
    FEB = "Feb"
    MAR = "Mar"
    APR = "Apr"
    MAY = "May"
    JUN = "Jun"
    JUL = "Jul"
    AUG = "Aug"
    SEP = "Sep"
    OCT = "Oct"
    NOV = "Nov"
    DEC = "Dec"


class SuccessMessageEnum(str, Enum):
    OPERATION_SUCCESSFUL = _("Operation successful")
    ACCOUNT_DELETED = _("compte supprimé avec succès")
    ACCOUNT_ACTIVATED = _("Account successfully activated")
    OTP_SENT = _("OTP sent successfully")
    OTP_SENT_FR = _("Code OTP envoyé avec succès")
    DISH_DELETED = _("Dish deleted successfully")
    DRINK_DELETED = _("Drink deleted successfully")
    TOKEN_GENERATED = _("Token generated successfully")
    TOKEN_REFRESHED = _("Token refreshed successfully")


class ErrorCodeEnum(str, Enum):
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    OTP_INVALID = "OTP_INVALID"
    PHONE_REQUIRED = "PHONE_REQUIRED"
    PHONE_INVALID_FORMAT = "PHONE_INVALID_FORMAT"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ACCOUNT_NOT_ACTIVATED = "ACCOUNT_NOT_ACTIVATED"
    OTP_SEND_FAILED = "OTP_SEND_FAILED"
    OTP_PROVIDER_ERROR = "OTP_PROVIDER_ERROR"
    OTP_DELIVERY_FAILED = "OTP_DELIVERY_FAILED"
    MISSING_PARAMETERS = "MISSING_PARAMETERS"
    INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
    INVALID_DATA = "INVALID_DATA"
    INVALID_ORDER_STATUS = "INVALID_ORDER_STATUS"
    TRANSITION_ERROR = "TRANSITION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    API_ERROR = "API_ERROR"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    TOKEN_NOT_VALID = "token_not_valid"
    UNAUTHORIZED = "UNAUTHORIZED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    UPDATE_FAILED = "UPDATE_FAILED"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class ErrorMessageEnum(str, Enum):
    INVALID_DATE_FORMAT = _("Invalid date format. ISO 8601 format is expected. Ex: 2024-01-01T00:00:00Z")
    MISSING_PARAMETERS = _("start_date and end_date are required")
    INVALID_OTP_CODE = _("Invalid OTP code")
    PHONE_REQUIRED = _("Phone number is required")
    PHONE_INVALID_FORMAT = _("Invalid phone format")
    USER_NOT_FOUND = _("User not found")
    ACCOUNT_NOT_ACTIVATED = _("Account not activated")
    OTP_SEND_FAILED = _("Failed to send OTP")
    OTP_PROVIDER_ERROR = _("OTP provider error")
    OTP_DELIVERY_FAILED = _("OTP delivery failed")
    INVALID_DATA = _("Invalid data")
    INVALID_USER = _("Invalid user")
    INTERNAL_SERVER_ERROR = _("An error occurred")
    TOKEN_NOT_VALID = _("Token is invalid or expired")
    VALIDATION_FAILED = _("Validation failed")
    PERMISSION_DENIED = _("Permission denied")
    NOT_FOUND = _("Resource not found")
    CUSTOMER_ALREADY_EXISTS = _("Customer already exists")
    ADDRESS_ALREADY_EXISTS = _("Address already exists")
    OPERATION_FAILED = _("Operation failed")
    SEARCH_INVALID_CHARACTERS = _(
        "Le champ de recherche contient des caractères non autorisés. "
        "Seuls les lettres, chiffres, espaces, tirets et apostrophes sont acceptés."
    )
    INVALID_DATE_RANGE = _("La date de début ne peut pas être supérieure à la date de fin.")
