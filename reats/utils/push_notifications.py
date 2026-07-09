import json
import logging
import os
from typing import Any, Sequence

import firebase_admin
from django.apps import apps
from firebase_admin import credentials, messaging

from utils.enums import CancelledByEnum, OrderStatusEnum

logger = logging.getLogger("reats_logger")

_firebase_initialized = False


def initialize_firebase() -> bool:
    global _firebase_initialized
    if _firebase_initialized:
        return True

    if firebase_admin._apps:
        _firebase_initialized = True
        return True

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON_PATH")
    cred_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized using certificate file.")
        elif cred_json_str:
            cred_info = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_info)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized using JSON string from environment.")
        else:
            logger.warning("Firebase credentials not configured. Push notifications will run in DRY RUN mode.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}. Push notifications will run in DRY RUN mode.")

    return _firebase_initialized


def send_push_notification(
    tokens: Sequence[str], title: str, body: str, data: dict[str, str] | None = None
) -> dict[str, Any]:
    """
    Sends a push notification to a list of tokens.
    """
    if not tokens:
        return {"success_count": 0, "failure_count": 0}

    initialized = initialize_firebase()

    if not initialized:
        logger.info(f"[FCM DRY RUN] Send to tokens={tokens} | Title='{title}' | Body='{body}' | Data={data}")
        return {"success_count": len(tokens), "failure_count": 0, "dry_run": True}

    message = messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
    )

    try:
        response = messaging.send_each_for_multicast(message)
        logger.info(f"FCM multicast success count: {response.success_count}, failure count: {response.failure_count}")

        if response.failure_count > 0:
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_token = tokens[idx]
                    logger.warning(f"Failed to send to token {failed_token}: {resp.exception}")
                    deactivate_token(failed_token)

        return {"success_count": response.success_count, "failure_count": response.failure_count, "dry_run": False}
    except Exception as e:
        logger.error(f"Error sending FCM multicast: {e}")
        return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}


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


def handle_order_status_change(order: Any, previous_status: Any, new_status: Any) -> None:
    """
    Dispatches push notifications based on order status transition.
    """
    # Convert enum objects to string values to be consistent
    prev_status_str = previous_status.value if hasattr(previous_status, "value") else str(previous_status)
    new_status_str = new_status.value if hasattr(new_status, "value") else str(new_status)

    # Avoid dispatching if status hasn't changed
    if prev_status_str == new_status_str:
        return

    data = {"order_id": str(order.id), "status": new_status_str}

    # 1. PENDING: Order placed, waiting for cooker
    if new_status_str == OrderStatusEnum.PENDING.value:
        send_notification_to_cooker(
            order.cooker,
            title="Nouvelle commande !",
            body=f"Vous avez reçu une nouvelle commande #{order.id} en attente d'acceptation.",
            data=data,
        )

    # 2. ACCEPTED: Cooker accepted the order
    elif new_status_str == OrderStatusEnum.ACCEPTED.value:
        send_notification_to_customer(
            order.customer,
            title="Commande acceptée !",
            body=f"Votre commande #{order.id} a été acceptée par le cuisinier.",
            data=data,
        )

    # 3. PREPARING: Cooker is preparing the order
    elif new_status_str == OrderStatusEnum.PREPARING.value:
        send_notification_to_customer(
            order.customer,
            title="En cours de préparation",
            body=f"Le cuisinier prépare votre commande #{order.id}.",
            data=data,
        )

    # 4. READY: Order is ready
    elif new_status_str == OrderStatusEnum.READY.value:
        send_notification_to_customer(
            order.customer,
            title="Commande prête !",
            body=f"Votre commande #{order.id} est prête !",
            data=data,
        )
        if order.delivery_man:
            send_notification_to_deliverer(
                order.delivery_man,
                title="Commande prête à être récupérée",
                body=f"La commande #{order.id} est prête chez le cuisinier.",
                data=data,
            )

    # 5. DELIVERING: Order is on the way
    elif new_status_str == OrderStatusEnum.DELIVERING.value:
        send_notification_to_customer(
            order.customer,
            title="Commande en cours de livraison",
            body="Le livreur est en route avec votre commande.",
            data=data,
        )

    # 6. COMPLETED: Order is completed
    elif new_status_str == OrderStatusEnum.COMPLETED.value:
        send_notification_to_customer(
            order.customer,
            title="Commande livrée !",
            body=f"Votre commande #{order.id} a été livrée. Bon appétit !",
            data=data,
        )

    # 7. CANCELLED: Order cancelled
    elif new_status_str == OrderStatusEnum.CANCELLED.value:
        cancelled_by = getattr(order, "cancelled_by", None)
        if cancelled_by == CancelledByEnum.COOKER.value:
            send_notification_to_customer(
                order.customer,
                title="Commande annulée",
                body=f"Votre commande #{order.id} a été annulée par le cuisinier.",
                data=data,
            )
        elif cancelled_by == CancelledByEnum.CUSTOMER.value:
            send_notification_to_cooker(
                order.cooker,
                title="Commande annulée",
                body=f"La commande #{order.id} a été annulée par le client.",
                data=data,
            )
            if order.delivery_man:
                send_notification_to_deliverer(
                    order.delivery_man,
                    title="Commande annulée",
                    body=f"La commande #{order.id} a été annulée par le client.",
                    data=data,
                )

    # 8. NOT_ACCEPTED: Cooker did not accept the order
    elif new_status_str == OrderStatusEnum.NOT_ACCEPTED.value:
        send_notification_to_customer(
            order.customer,
            title="Commande non acceptée",
            body=f"Désolé, votre commande #{order.id} n'a pas pu être acceptée par le cuisinier à temps.",
            data=data,
        )
