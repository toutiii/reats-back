import pytest
from core_app.models import DeliverFCMDeviceModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def deliverer_id() -> int:
    return 1


@pytest.mark.django_db
def test_create_deliverer_device_token_success(
    auth_headers: dict,
    client: APIClient,
    deliverer_id: int,
    deliverer_devices_path: str,
) -> None:
    DeliverFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_deliverer_123",
        "device_type": "android",
    }

    response = client.post(
        deliverer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("success") is True

    assert DeliverFCMDeviceModel.objects.count() == 1
    device = DeliverFCMDeviceModel.objects.first()
    assert device is not None
    assert device.token == "fcm_token_deliverer_123"
    assert device.device_type == "android"
    assert device.deliver.id == deliverer_id
    assert device.is_active is True


@pytest.mark.django_db
def test_create_deliverer_device_token_duplicate_overwrites(
    auth_headers: dict,
    client: APIClient,
    deliverer_id: int,
    deliverer_devices_path: str,
) -> None:
    DeliverFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_deliverer_123",
        "device_type": "android",
    }

    # First POST
    response = client.post(
        deliverer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Second POST
    second_request_response = client.post(
        deliverer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    assert second_request_response.status_code == status.HTTP_200_OK
    assert DeliverFCMDeviceModel.objects.count() == 1


@pytest.mark.django_db
def test_get_deliverer_devices_only_returns_own(
    auth_headers: dict,
    client: APIClient,
    deliverer_id: int,
    deliverer_devices_path: str,
) -> None:
    DeliverFCMDeviceModel.objects.all().delete()

    DeliverFCMDeviceModel.objects.create(
        deliver_id=deliverer_id,
        token="token_deliverer_1",
        device_type="ios",
    )

    DeliverFCMDeviceModel.objects.create(
        deliver_id=2,
        token="token_deliverer_2",
        device_type="android",
    )

    response = client.get(
        deliverer_devices_path,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    assert len(data) == 1
    assert data[0]["token"] == "token_deliverer_1"


@pytest.mark.django_db
def test_deregister_deliverer_device_token(
    auth_headers: dict,
    client: APIClient,
    deliverer_id: int,
    deliverer_devices_path: str,
) -> None:
    DeliverFCMDeviceModel.objects.all().delete()

    DeliverFCMDeviceModel.objects.create(
        deliver_id=deliverer_id,
        token="fcm_token_to_delete",
        device_type="android",
    )

    response = client.post(
        f"{deliverer_devices_path}deregister/",
        {"token": "fcm_token_to_delete"},
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("success") is True
    assert DeliverFCMDeviceModel.objects.count() == 0
