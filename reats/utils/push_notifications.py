from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

import firebase_admin
from django.apps import apps
from firebase_admin import credentials, exceptions, messaging

from utils.enums import CancelledByEnum, OrderStatusEnum

if TYPE_CHECKING:
    from core_app.models import OrderModel

logger = logging.getLogger("reats_logger")


NOTIFICATION_TEMPLATES = {
    "pending_cooker": ("Nouvelle commande !", "Nouvelle commande ! Veuillez la consulter pour l'accepter."),
    "accepted_customer": ("Commande acceptée !", "{cooker_name} a accepté votre commande !"),
    "accepted_deliverer_time": (
        "Commande acceptée par le cuisinier",
        "La commande sera disponible chez {cooker_name_lower} dans {prep_time} minutes.",
    ),
    "accepted_deliverer_soon": (
        "Commande acceptée par le cuisinier",
        "La commande sera disponible chez {cooker_name_lower} d'ici peu.",
    ),
    "preparing_customer": ("En cours de préparation", "Le cuisinier prépare votre commande #{order_id}."),
    "ready_customer": ("Commande prête !", "Votre commande #{order_id} est prête !"),
    "ready_deliverer": (
        "Commande prête à être récupérée",
        "La commande #{order_id} peut-être retirée chez {cooker_name_lower}.",
    ),
    "delivering_customer": ("Commande en cours de livraison", "{delivery_name} arrive avec votre commande !"),
    "completed_customer": ("Commande livrée !", "Votre commande a été livrée. Bon appétit !"),
    "cancelled_by_cooker": ("Commande annulée", "{cooker_name} a annulé votre commande."),
    "cancelled_by_customer": ("Commande annulée", "La commande #{order_id} a été annulée par le client."),
    "not_accepted": ("Commande non acceptée", "{cooker_name} n'a pas pu accepter votre commande."),
}


def _get_msg(key: str, **kwargs) -> tuple[str, str]:
    title, body = NOTIFICATION_TEMPLATES[key]
    return title.format(**kwargs), body.format(**kwargs)


def _is_initialized() -> bool:
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        return False


def _load_credentials() -> credentials.Certificate | None:
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON_PATH")
    if cred_path and os.path.exists(cred_path):
        logger.info("Credentials Firebase chargés depuis le fichier de certificat.")
        return credentials.Certificate(cred_path)

    cred_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if cred_json_str:
        logger.info("Credentials Firebase chargés depuis la variable d'environnement JSON.")
        return credentials.Certificate(json.loads(cred_json_str))

    return None


def initialize_firebase() -> bool:
    if _is_initialized():
        return True

    try:
        cred = _load_credentials()
    except Exception as e:
        logger.error(f"Credentials Firebase invalides : {e}. Push notifications en mode DRY RUN.")
        return False

    if cred is None:
        logger.warning("Credentials Firebase non configurés. Push notifications en mode DRY RUN.")
        return False

    try:
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f"Échec de l'initialisation du SDK Firebase Admin : {e}. Push notifications en mode DRY RUN.")
        return False

    logger.info("SDK Firebase Admin initialisé.")
    return True


@dataclass(frozen=True)
class PushResult:
    success_count: int
    failure_count: int
    dry_run: bool = False
    error: str | None = None


def _build_message(
    tokens: Sequence[str], title: str, body: str, data: dict[str, str] | None
) -> messaging.MulticastMessage:
    return messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )


def _handle_failures(tokens: Sequence[str], responses: Sequence[messaging.SendResponse]) -> None:
    for token, resp in zip(tokens, responses):
        if resp.success:
            continue
        logger.warning(f"Échec d'envoi vers le token {token} : {resp.exception}")
        deactivate_token(token)


def send_push_notification(
    tokens: Sequence[str], title: str, body: str, data: dict[str, str] | None = None
) -> PushResult:
    if not tokens:
        return PushResult(success_count=0, failure_count=0)

    if not initialize_firebase():
        logger.info(f"[FCM DRY RUN] tokens={tokens} | Title='{title}' | Body='{body}' | Data={data}")
        return PushResult(success_count=len(tokens), failure_count=0, dry_run=True)

    message = _build_message(tokens, title, body, data)

    try:
        response = messaging.send_each_for_multicast(message)
    except exceptions.FirebaseError as e:
        logger.error(f"Erreur lors de l'envoi FCM multicast : {e}")
        return PushResult(success_count=0, failure_count=len(tokens), error=str(e))

    logger.info(f"FCM multicast — succès : {response.success_count}, échecs : {response.failure_count}")
    _handle_failures(tokens, response.responses)

    return PushResult(
        success_count=response.success_count,
        failure_count=response.failure_count,
    )


def deactivate_token(token: str) -> None:
    """
    Deactivates an invalid/expired token across all device token models.
    """
    CustomerFCMDeviceModel = apps.get_model("core_app", "CustomerFCMDeviceModel")
    CookerFCMDeviceModel = apps.get_model("core_app", "CookerFCMDeviceModel")
    DeliverFCMDeviceModel = apps.get_model("core_app", "DeliverFCMDeviceModel")

    CustomerFCMDeviceModel.objects.filter(token=token).update(is_active=False)
    CookerFCMDeviceModel.objects.filter(token=token).update(is_active=False)
    DeliverFCMDeviceModel.objects.filter(token=token).update(is_active=False)


def send_notification_to_customer(customer: Any, title: str, body: str, data: dict[str, str] | None = None) -> None:
    CustomerFCMDeviceModel = apps.get_model("core_app", "CustomerFCMDeviceModel")
    tokens = list(
        CustomerFCMDeviceModel.objects.filter(customer=customer, is_active=True).values_list("token", flat=True)
    )
    if tokens:
        send_push_notification(tokens, title, body, data)


def send_notification_to_cooker(cooker: Any, title: str, body: str, data: dict[str, str] | None = None) -> None:
    CookerFCMDeviceModel = apps.get_model("core_app", "CookerFCMDeviceModel")
    tokens = list(CookerFCMDeviceModel.objects.filter(cooker=cooker, is_active=True).values_list("token", flat=True))
    if tokens:
        send_push_notification(tokens, title, body, data)


def send_notification_to_deliverer(deliverer: Any, title: str, body: str, data: dict[str, str] | None = None) -> None:
    DeliverFCMDeviceModel = apps.get_model("core_app", "DeliverFCMDeviceModel")
    tokens = list(
        DeliverFCMDeviceModel.objects.filter(deliver=deliverer, is_active=True).values_list("token", flat=True)
    )
    if tokens:
        send_push_notification(tokens, title, body, data)


def handle_order_status_change(
    order: OrderModel, previous_status: OrderStatusEnum, new_status: OrderStatusEnum
) -> None:
    """
    Dispatches push notifications based on order status transition.
    """
    # Avoid dispatching if status hasn't changed
    if previous_status == new_status:
        return

    data = {"order_id": str(order.id), "status": new_status.value}

    # Common variables used in templates
    cooker_name = order.cooker.firstname if order.cooker else "Le cuisinier"
    cooker_name_lower = order.cooker.firstname if order.cooker else "le cuisinier"
    delivery_name = order.delivery_man.firstname if order.delivery_man else "Le livreur"
    ctx = {
        "order_id": order.id,
        "cooker_name": cooker_name,
        "cooker_name_lower": cooker_name_lower,
        "delivery_name": delivery_name,
    }

    # 1. PENDING: Order placed, waiting for cooker
    if new_status == OrderStatusEnum.PENDING:
        title, body = _get_msg("pending_cooker", **ctx)
        send_notification_to_cooker(order.cooker, title, body, data)

    # 2. ACCEPTED: Cooker accepted the order
    elif new_status == OrderStatusEnum.ACCEPTED:
        title, body = _get_msg("accepted_customer", **ctx)
        send_notification_to_customer(order.customer, title, body, data)

        if order.delivery_man and not order.is_scheduled:
            prep_times = [
                item.dish.preparation_time
                for item in order.dishes_items.select_related("dish")  # type: ignore
                if item.dish and item.dish.preparation_time is not None
            ]
            prep_time = max(prep_times) if prep_times else 0

            if prep_time > 0:
                title, body = _get_msg("accepted_deliverer_time", prep_time=prep_time, **ctx)
            else:
                title, body = _get_msg("accepted_deliverer_soon", **ctx)

            send_notification_to_deliverer(order.delivery_man, title, body, data)

    # 3. PREPARING: Cooker is preparing the order
    elif new_status == OrderStatusEnum.PREPARING:
        title, body = _get_msg("preparing_customer", **ctx)
        send_notification_to_customer(order.customer, title, body, data)

    # 4. READY: Order is ready
    elif new_status == OrderStatusEnum.READY:
        title, body = _get_msg("ready_customer", **ctx)
        send_notification_to_customer(order.customer, title, body, data)

        if order.delivery_man:
            title, body = _get_msg("ready_deliverer", **ctx)
            send_notification_to_deliverer(order.delivery_man, title, body, data)

    # 5. DELIVERING: Order is on the way
    elif new_status == OrderStatusEnum.DELIVERING:
        title, body = _get_msg("delivering_customer", **ctx)
        send_notification_to_customer(order.customer, title, body, data)

    # 6. COMPLETED: Order is completed
    elif new_status == OrderStatusEnum.COMPLETED:
        title, body = _get_msg("completed_customer", **ctx)
        send_notification_to_customer(order.customer, title, body, data)

    # 7. CANCELLED: Order cancelled
    elif new_status == OrderStatusEnum.CANCELLED:
        cancelled_by = getattr(order, "cancelled_by", None)
        if cancelled_by == CancelledByEnum.COOKER.value:
            title, body = _get_msg("cancelled_by_cooker", **ctx)
            send_notification_to_customer(order.customer, title, body, data)
        elif cancelled_by == CancelledByEnum.CUSTOMER.value:
            title, body = _get_msg("cancelled_by_customer", **ctx)
            send_notification_to_cooker(order.cooker, title, body, data)
            if order.delivery_man and previous_status not in (OrderStatusEnum.PENDING, OrderStatusEnum.NOT_ACCEPTED):
                send_notification_to_deliverer(order.delivery_man, title, body, data)

    # 8. NOT_ACCEPTED: Cooker did not accept the order
    elif new_status == OrderStatusEnum.NOT_ACCEPTED:
        title, body = _get_msg("not_accepted", **ctx)
        send_notification_to_customer(order.customer, title, body, data)
