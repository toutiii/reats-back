import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Type, Union

import boto3
import phonenumbers
import stripe
import stripe.error
import stripe.util
from botocore.exceptions import ClientError
from core_app.models import CookerModel, CustomerModel, DeliverModel, OrderModel
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from phonenumbers.phonenumberutil import NumberParseException

from utils.enums import OrderStatusEnum

logger = logging.getLogger("watchtower-logger")


def _get_s3_client():
    """
    Lazy factory: creates a fresh boto3 S3 client on every call.

    Why not module-level?
    - This module is imported at Django startup, BEFORE load_dotenv() runs.
    - A module-level client would have AWS_REGION=None and stale/missing
      credentials, producing presigned URLs signed with no region (defaulting
      to the global s3.amazonaws.com endpoint).
    - AWS rejects those URLs because the credential region (eu-central-1)
      does not match the endpoint region (us-east-1 / global).

    Why virtual addressing style?
    - Generates URLs as https://<bucket>.s3.<region>.amazonaws.com/<key>
    - The hostname region always matches the signing region → no mismatch.
    """
    region = (os.getenv("AWS_REGION") or "").strip("\"'")
    if not region:
        logger.error("[S3] AWS_REGION is not set — S3 calls will fail.")
    return boto3.client(
        "s3",
        region_name=region,
        config=boto3.session.Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        ),
    )


pinpoint_client = boto3.client("pinpoint", region_name=os.getenv("AWS_REGION"))
stripe.api_key = settings.STRIPE_PRIVATE_API_KEY


def compute_start_date(timeframe: str) -> datetime:
    """
    Compute the starting date based on the given timeframe.

    Args:
        timeframe (str): Can be "week", "month", or "year".

    Returns:
        datetime: The computed start date at midnight in UTC.
    """
    now = datetime.now(timezone.utc)

    if timeframe == "week":
        # Calculate the most recent Monday
        days_to_subtract = now.weekday()
        start_date = now - timedelta(days=days_to_subtract)

    elif timeframe == "month":
        # Set the date to the first day of the current month
        start_date = now.replace(day=1)

    elif timeframe == "year":
        # Set the date to the first day of the current year
        start_date = now.replace(month=1, day=1)

    # Set the time to midnight
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_date


def upload_image_to_s3(image: InMemoryUploadedFile, image_path: str) -> None:
    try:
        _get_s3_client().upload_fileobj(
            image,
            os.getenv("AWS_S3_BUCKET"),
            image_path,
        )
    except ClientError as err:
        logger.error(err)
    else:
        logger.info(f"{image_path} has been uploaded to S3.")


def get_pre_signed_url(key: str) -> str:
    bucket = os.getenv("AWS_S3_BUCKET")
    try:
        url = _get_s3_client().generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=3600,
        )
    except ClientError as err:
        logger.error(f"[S3] Failed to generate presigned URL for key={key}: {err}")
        return ""
    else:
        logger.debug(f"[S3] Presigned URL generated for key={key}")

    return url


def delete_s3_object(key: str) -> None:
    try:
        _get_s3_client().delete_object(Bucket=os.getenv("AWS_S3_BUCKET"), Key=key)
    except ClientError as err:
        logger.error(err)
    else:
        logger.info(f"{key} has been removed from {os.getenv('AWS_S3_BUCKET')} bucket")


def format_phone(phone: str) -> str:
    if phone in settings.PHONE_BLACK_LIST:
        raise NumberParseException(
            NumberParseException.NOT_A_NUMBER,
            "This phone number is forbidden",
        )

    e164_phone_number = phonenumbers.format_number(
        phonenumbers.parse(
            phone,
            settings.PHONE_REGION,
        ),
        phonenumbers.PhoneNumberFormat.E164,
    )
    return e164_phone_number


def generate_ref_id(phone: str):
    return hashlib.md5(phone.encode()).hexdigest()


def send_otp(phone: str) -> Union[dict, None]:
    try:
        response: dict = pinpoint_client.send_otp_message(
            ApplicationId=os.getenv("AWS_PINPOINT_APP_ID"),
            SendOTPMessageRequestParameters={
                "Channel": os.getenv("AWS_PINPOINT_CHANNEL"),
                "BrandName": os.getenv("AWS_PINPOINT_BRAND_NAME"),
                "CodeLength": int(os.getenv("AWS_PINPOINT_CODE_LENGTH", "6")),
                "ValidityPeriod": int(os.getenv("AWS_PINPOINT_VALIDITY_PERIOD", "10")),
                "AllowedAttempts": int(os.getenv("AWS_PINPOINT_ALLOWED_ATTEMPTS", "3")),
                "Language": os.getenv("AWS_PINPOINT_LANGUAGE"),
                "OriginationIdentity": os.getenv("AWS_SENDER_ID"),
                "DestinationIdentity": phone,
                "ReferenceId": generate_ref_id(phone),
            },
        )
        logger.info("Pinpoint send_otp_message response=%s", response)
        return response
    except ClientError as e:
        logger.info(e.response)
        return None


def is_otp_valid(data: dict) -> bool:
    try:
        response = pinpoint_client.verify_otp_message(
            ApplicationId=os.getenv("AWS_PINPOINT_APP_ID"),
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": format_phone(data["phone"]),
                "ReferenceId": generate_ref_id(format_phone(data["phone"])),
                "Otp": data["otp"],
            },
        )

    except ClientError as e:
        logger.info(e.response)
        return False

    return response["VerificationResponse"]["Valid"]


def activate_user(
    model: Type[Union[CookerModel, CustomerModel, DeliverModel]], data: dict
) -> Union[CookerModel, CustomerModel, DeliverModel]:
    """Active le compte et renvoie l'utilisateur, à qui l'appelant émettra ses tokens."""
    user = model.objects.get(phone=format_phone(data["phone"]))

    if not user.is_activated:
        user.is_activated = True
        user.save()

    return user


def get_stripe_customer_by_email(email: str) -> Union[stripe.Customer, None]:
    try:
        customer = stripe.Customer.list(email=email).data[0]
    except stripe.StripeError as e:
        logger.error(e)
        return None
    except IndexError:
        logger.info(f"No Stripe customer found with email {email}")
        return None

    return customer


def create_stripe_customer(
    user_data: dict,
    default_email_suffix: str,
) -> None:
    customer_default_email = user_data["phone"] + default_email_suffix
    customer: Union[stripe.Customer, None] = get_stripe_customer_by_email(customer_default_email)

    if customer:
        logger.info(f"Stripe customer with email {customer_default_email} already exists")
        return

    max_retries = 3
    retry_delay = 2  # Initial delay between retries in seconds
    customer_name = f"{user_data['firstname']} {user_data['lastname']}"

    for attempt in range(1, max_retries + 1):
        try:
            customer_response: dict = stripe.Customer.create(
                name=customer_name,
                phone=user_data["phone"],
                preferred_locales=["fr"],
                email=customer_default_email,
            )
        except (
            stripe.APIConnectionError,
            stripe.RateLimitError,
        ) as e:  # These exceptions are retryable
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                logger.error(f"Max retries exceeded. Unable to create Stripe customer {customer_name}")
                raise
            else:
                # Exponential backoff before the next retry
                sleep_time = retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
        except stripe.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise
        else:
            logger.info(f"Stripe customer {customer_default_email} created successfully")
            logger.debug("Updating user's stripe_id...")
            user: CustomerModel = CustomerModel.objects.get(phone=user_data["phone"])
            user.stripe_id = customer_response["id"]
            user.save()
            break


def compute_order_items_total_amount(order: OrderModel) -> float:
    dish_total = 0.0
    drink_total = 0.0

    for dish_item in order.dishes_items.all():  # type: ignore
        dish_total += dish_item.dish.price * dish_item.dish_quantity

    for drink_item in order.drinks_items.all():  # type: ignore
        drink_total += drink_item.drink.price * drink_item.drink_quantity

    return round(dish_total + drink_total, 2)


def compute_order_total_amount(order: OrderModel) -> int:
    order_items_total = compute_order_items_total_amount(order)
    service_fees = round(order_items_total * settings.SERVICE_FEES_RATE, 2)

    return order_items_total + order.delivery_fees + service_fees


def create_payment_intent(order: OrderModel) -> dict:
    order_total_amount: Union[int, float] = compute_order_total_amount(order)
    order_total_amount_in_cents: int = int(order_total_amount * 100)
    order_customer: CustomerModel = order.customer

    try:
        response = stripe.PaymentIntent.create(
            amount=order_total_amount_in_cents,
            currency=settings.DEFAULT_CURRENCY,
            automatic_payment_methods={"enabled": True},
            customer=order_customer.stripe_id,
            capture_method="manual",
        )
    except stripe.StripeError as e:
        logger.error(f"Failed to create payment intent for order {order.id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create payment intent for order {order.id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Payment intent for order {order.id} created successfully")
        return stripe.util.convert_to_dict(response)  # ty: ignore[unresolved-attribute]


def update_payment_intent(
    order: OrderModel,
) -> None:
    order_total_amount: Union[int, float] = compute_order_total_amount(order)
    order_total_amount_in_cents: int = int(order_total_amount * 100)
    try:
        response = stripe.PaymentIntent.modify(
            order.stripe_payment_intent_id,
            amount=order_total_amount_in_cents,
        )
    except stripe.StripeError as e:
        logger.error(f"Failed to update payment intent {order.stripe_payment_intent_id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to update payment intent {order.stripe_payment_intent_id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Payment intent {order.stripe_payment_intent_id} updated successfully")
        logger.debug(response)


def delete_stripe_customer(stripe_id: str) -> None:
    try:
        response = stripe.Customer.delete(stripe_id)
    except stripe.StripeError as e:
        logger.error(f"Failed to delete Stripe customer {stripe_id}")
        logger.error(f"Stripe error: {e}")
    except Exception as e:
        logger.error(f"Failed to delete Stripe customer {stripe_id}")
        logger.error(f"An unexpected error occurred: {e}")
    else:
        logger.info(f"Stripe customer {stripe_id} deleted successfully")
        logger.debug(response)


def create_stripe_ephemeral_key(customer: CustomerModel) -> str:
    try:
        response = stripe.EphemeralKey.create(
            customer=customer.stripe_id,
            stripe_version="2024-06-20",
        )
    except stripe.StripeError as e:
        logger.error(f"Failed to create ephemeral key for customer {customer.id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create ephemeral key for customer {customer.id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Ephemeral key for customer {customer.id} created successfully")
        logger.debug(response)
        return response["secret"]


def is_event_from_stripe(request) -> bool:
    is_event_valid = False
    try:
        stripe.Webhook.construct_event(
            request.body,
            request.headers.get("stripe-signature"),
            settings.STRIPE_WEBHOOK_ENDPOINT_SIGNATURE,
        )
        is_event_valid = True
    except ValueError as e:
        logger.error(e)
    except stripe.error.SignatureVerificationError as e:  # ty: ignore[unresolved-attribute]
        logger.error(e)
    except Exception as e:
        logger.error(e)

    return is_event_valid


def create_stripe_refund(amount: int, payment_intent_id: str) -> None:
    try:
        response = stripe.Refund.create(
            amount=amount,
            payment_intent=payment_intent_id,
        )
    except stripe.StripeError as e:
        logger.error(f"Failed to create refund for payment intent {payment_intent_id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create refund for payment intent {payment_intent_id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Refund for payment intent {payment_intent_id} created successfully")
        logger.debug(response)


def compute_customer_cancellation_refund_amount(order: OrderModel) -> int:
    """
    Refund amount, in cents, for a customer cancelling an accepted or preparing order.

    The customer is refunded the full amount they paid (items sub-total, delivery
    fees and service fees) minus a cooker compensation, computed as a percentage of
    the items sub-total (settings.COOKER_COMPENSATION_RATE). The result is floored at 0.

    :param order: The order being cancelled
    :return: The amount to refund to the customer, in cents
    """
    total = Decimal(str(compute_order_total_amount(order)))
    sub_total = Decimal(str(compute_order_items_total_amount(order)))
    rate = Decimal(str(settings.COOKER_COMPENSATION_RATE))
    compensation = sub_total * rate / Decimal("100")
    refund_amount = (total - compensation) * Decimal("100")
    return max(int(refund_amount), 0)


def capture_payment_intent(order: OrderModel) -> None:
    """
    Capture the funds previously authorized on the order's payment intent.

    Called when the cooker accepts the order: this is the moment the customer
    is actually charged.
    """
    try:
        response = stripe.PaymentIntent.capture(order.stripe_payment_intent_id)
    except stripe.StripeError as e:
        logger.error(f"Failed to capture payment intent {order.stripe_payment_intent_id} for order {order.id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to capture payment intent {order.stripe_payment_intent_id} for order {order.id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Payment intent {order.stripe_payment_intent_id} captured successfully for order {order.id}")
        logger.debug(response)


def cancel_payment_intent(order: OrderModel) -> None:
    """
    Cancel the order's payment intent, releasing the authorization hold.

    Used when an order ends before the funds are captured (acceptance), e.g. a
    customer cancellation while still pending, or a cooker acceptance timeout.
    No money has been charged, so there is nothing to refund.
    """
    try:
        response = stripe.PaymentIntent.cancel(order.stripe_payment_intent_id)
    except stripe.StripeError as e:
        logger.error(f"Failed to cancel payment intent {order.stripe_payment_intent_id} for order {order.id}")
        logger.error(f"Stripe error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to cancel payment intent {order.stripe_payment_intent_id} for order {order.id}")
        logger.error(f"An unexpected error occurred: {e}")
        raise
    else:
        logger.info(f"Payment intent {order.stripe_payment_intent_id} cancelled successfully for order {order.id}")
        logger.debug(response)


def get_delivery_fee(distance: float) -> float:
    """
    Calculate the delivery fee based on the distance.

    :param distance: The distance in meters
    :return: The delivery fee
    """
    base_fee = 2.5  # Base fee in euros
    per_km_rate = 0.5  # Rate per kilometer in euros

    # Convert distance to kilometers
    distance_km = distance / 1000

    # Calculate the delivery fee
    delivery_fee = base_fee + (distance_km * per_km_rate)
    return round(delivery_fee, 2)


def update_cooker_acceptance_rate(
    instance: OrderModel,
    new_status: str,
) -> None:
    """
    Update the cookers's acceptance rate based on the new status.

    Basically, only PROCESSING and CANCELLED_BY_COOKER statuses are taken into account.

    :param instance: The cooker instance
    :param new_status: The new status
    """

    if new_status in (OrderStatusEnum.CANCELLED, OrderStatusEnum.NOT_ACCEPTED):
        new_value = instance.cooker.acceptance_rate - settings.ACCEPTANCE_RATE_DECREASE_VALUE
    elif new_status == OrderStatusEnum.COMPLETED:
        new_value = instance.cooker.acceptance_rate + settings.ACCEPTANCE_RATE_INCREASE_VALUE
    else:
        logger.info(f"Status {new_status} is not taken into account")
        return

    if new_value <= 0:
        new_value = 0

    if new_value >= 100:
        new_value = 100

    instance.cooker.acceptance_rate = new_value
    instance.cooker.last_acceptance_rate_update_date = datetime.now(timezone.utc)
    instance.cooker.save()
