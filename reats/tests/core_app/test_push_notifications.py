from unittest.mock import MagicMock, patch

import pytest
from core_app.models import (
    CookerFCMDeviceModel,
    CookerModel,
    CustomerFCMDeviceModel,
    CustomerModel,
    DeliverFCMDeviceModel,
    DeliverModel,
    OrderModel,
)
from utils.enums import CancelledByEnum, OrderStatusEnum
from utils.push_notifications import (
    deactivate_token,
    handle_order_status_change,
    initialize_firebase,
    send_push_notification,
)


@pytest.fixture
def mock_firebase_env():
    with patch.dict(
        "os.environ",
        {
            "FIREBASE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        },
    ):
        yield


@pytest.mark.django_db
class TestPushNotifications:
    def test_initialize_firebase_dry_run(self):
        # When no env variable is set, it returns False (dry run)
        with patch.dict("os.environ", {}, clear=True):
            with patch("firebase_admin.initialize_app") as mock_init:
                res = initialize_firebase()
                assert res is False
                mock_init.assert_not_called()

    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.credentials.Certificate")
    def test_initialize_firebase_success(self, mock_cert, mock_init, mock_firebase_env):
        with patch("firebase_admin._apps", []):
            res = initialize_firebase()
            assert res is True
            mock_init.assert_called_once()

    def test_send_push_notification_dry_run(self):
        # Without firebase initialization, it runs in dry run mode
        with patch("utils.push_notifications.initialize_firebase", return_value=False):
            res = send_push_notification(tokens=["token_123"], title="Hello", body="World")
            assert res["dry_run"] is True
            assert res["success_count"] == 1

    @patch("firebase_admin.messaging.send_each_for_multicast")
    def test_send_push_notification_success(self, mock_send):
        mock_response = MagicMock()
        mock_response.success_count = 1
        mock_response.failure_count = 0
        mock_send.return_value = mock_response

        with patch("utils.push_notifications.initialize_firebase", return_value=True):
            res = send_push_notification(tokens=["token_123"], title="Hello", body="World")
            assert res["dry_run"] is False
            assert res["success_count"] == 1
            assert res["failure_count"] == 0
            mock_send.assert_called_once()

    @patch("firebase_admin.messaging.send_each_for_multicast")
    @patch("utils.push_notifications.deactivate_token")
    def test_send_push_notification_partial_failure(self, mock_deactivate, mock_send):
        mock_response = MagicMock()
        mock_response.success_count = 1
        mock_response.failure_count = 1

        mock_resp_success = MagicMock()
        mock_resp_success.success = True

        mock_resp_fail = MagicMock()
        mock_resp_fail.success = False
        mock_resp_fail.exception = Exception("Token expired")

        mock_response.responses = [mock_resp_success, mock_resp_fail]
        mock_send.return_value = mock_response

        with patch("utils.push_notifications.initialize_firebase", return_value=True):
            res = send_push_notification(tokens=["token_ok", "token_bad"], title="Hello", body="World")
            assert res["success_count"] == 1
            assert res["failure_count"] == 1
            mock_deactivate.assert_called_once_with("token_bad")

    def test_deactivate_token(self):
        # Create active tokens
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="token_cust", device_type="ios")
        CookerFCMDeviceModel.objects.create(cooker_id=1, token="token_cook", device_type="android")
        DeliverFCMDeviceModel.objects.create(deliver_id=1, token="token_del", device_type="ios")

        # Deactivate one
        deactivate_token("token_cook")

        assert CustomerFCMDeviceModel.objects.get(token="token_cust").is_active is True
        assert CookerFCMDeviceModel.objects.get(token="token_cook").is_active is False
        assert DeliverFCMDeviceModel.objects.get(token="token_del").is_active is True

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_pending(self, mock_send_push):
        # Clear existing tokens to ensure we control them
        CookerFCMDeviceModel.objects.all().delete()
        CookerFCMDeviceModel.objects.create(cooker_id=1, token="cooker_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.cooker = CookerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.DRAFT, OrderStatusEnum.PENDING)

        mock_send_push.assert_called_once_with(
            ["cooker_token"],
            "Nouvelle commande !",
            f"Vous avez reçu une nouvelle commande #{order.id} en attente d'acceptation.",
            {"order_id": str(order.id), "status": "pending"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_accepted(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.PENDING, OrderStatusEnum.ACCEPTED)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "Commande acceptée !",
            f"Votre commande #{order.id} a été acceptée par le cuisinier.",
            {"order_id": str(order.id), "status": "accepted"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_preparing(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.ACCEPTED, OrderStatusEnum.PREPARING)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "En cours de préparation",
            f"Le cuisinier prépare votre commande #{order.id}.",
            {"order_id": str(order.id), "status": "preparing"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_ready(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")
        DeliverFCMDeviceModel.objects.all().delete()
        DeliverFCMDeviceModel.objects.create(deliver_id=1, token="deliver_token", device_type="android")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.delivery_man = DeliverModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.PREPARING, OrderStatusEnum.READY)

        assert mock_send_push.call_count == 2
        mock_send_push.assert_any_call(
            ["customer_token"],
            "Commande prête !",
            f"Votre commande #{order.id} est prête !",
            {"order_id": str(order.id), "status": "ready"},
        )
        mock_send_push.assert_any_call(
            ["deliver_token"],
            "Commande prête à être récupérée",
            f"La commande #{order.id} est prête chez le cuisinier.",
            {"order_id": str(order.id), "status": "ready"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_delivering(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.READY, OrderStatusEnum.DELIVERING)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "Commande en cours de livraison",
            "Le livreur est en route avec votre commande.",
            {"order_id": str(order.id), "status": "delivering"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_completed(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.DELIVERING, OrderStatusEnum.COMPLETED)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "Commande livrée !",
            f"Votre commande #{order.id} a été livrée. Bon appétit !",
            {"order_id": str(order.id), "status": "completed"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_cancelled_by_cooker(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.cancelled_by = CancelledByEnum.COOKER.value
        order.save()

        handle_order_status_change(order, OrderStatusEnum.PENDING, OrderStatusEnum.CANCELLED)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "Commande annulée",
            f"Votre commande #{order.id} a été annulée par le cuisinier.",
            {"order_id": str(order.id), "status": "cancelled"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_cancelled_by_customer(self, mock_send_push):
        CookerFCMDeviceModel.objects.all().delete()
        CookerFCMDeviceModel.objects.create(cooker_id=1, token="cooker_token", device_type="ios")
        DeliverFCMDeviceModel.objects.all().delete()
        DeliverFCMDeviceModel.objects.create(deliver_id=1, token="deliver_token", device_type="android")

        order = OrderModel.objects.get(id=1)
        order.cooker = CookerModel.objects.get(id=1)
        order.delivery_man = DeliverModel.objects.get(id=1)
        order.cancelled_by = CancelledByEnum.CUSTOMER.value
        order.save()

        handle_order_status_change(order, OrderStatusEnum.PENDING, OrderStatusEnum.CANCELLED)

        assert mock_send_push.call_count == 2
        mock_send_push.assert_any_call(
            ["cooker_token"],
            "Commande annulée",
            f"La commande #{order.id} a été annulée par le client.",
            {"order_id": str(order.id), "status": "cancelled"},
        )
        mock_send_push.assert_any_call(
            ["deliver_token"],
            "Commande annulée",
            f"La commande #{order.id} a été annulée par le client.",
            {"order_id": str(order.id), "status": "cancelled"},
        )

    @patch("utils.push_notifications.send_push_notification")
    def test_handle_order_status_change_not_accepted(self, mock_send_push):
        CustomerFCMDeviceModel.objects.all().delete()
        CustomerFCMDeviceModel.objects.create(customer_id=1, token="customer_token", device_type="ios")

        order = OrderModel.objects.get(id=1)
        order.customer = CustomerModel.objects.get(id=1)
        order.save()

        handle_order_status_change(order, OrderStatusEnum.PENDING, OrderStatusEnum.NOT_ACCEPTED)

        mock_send_push.assert_called_once_with(
            ["customer_token"],
            "Commande non acceptée",
            f"Désolé, votre commande #{order.id} n'a pas pu être acceptée par le cuisinier à temps.",
            {"order_id": str(order.id), "status": "not_accepted"},
        )
