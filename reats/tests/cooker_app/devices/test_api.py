import pytest
from core_app.models import CookerFCMDeviceModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.mark.django_db
def test_create_cooker_device_token_success(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cooker_devices_path: str,
) -> None:
    CookerFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_cooker_123",
        "device_type": "ios",
    }

    response = client.post(
        cooker_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("success") is True

    assert CookerFCMDeviceModel.objects.count() == 1
    device = CookerFCMDeviceModel.objects.first()
    assert device is not None
    assert device.token == "fcm_token_cooker_123"
    assert device.device_type == "ios"
    assert device.cooker.id == cooker_id
    assert device.is_active is True


@pytest.mark.django_db
def test_create_cooker_device_token_duplicate_overwrites(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cooker_devices_path: str,
) -> None:
    CookerFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_cooker_123",
        "device_type": "ios",
    }

    # First POST
    response = client.post(
        cooker_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Second POST
    response2 = client.post(
        cooker_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    assert response2.status_code == status.HTTP_200_OK
    assert CookerFCMDeviceModel.objects.count() == 1


@pytest.mark.django_db
def test_get_cooker_devices_only_returns_own(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cooker_devices_path: str,
) -> None:
    CookerFCMDeviceModel.objects.all().delete()

    CookerFCMDeviceModel.objects.create(
        cooker_id=cooker_id,
        token="token_cooker_1",
        device_type="ios",
    )

    CookerFCMDeviceModel.objects.create(
        cooker_id=2,
        token="token_cooker_2",
        device_type="android",
    )

    response = client.get(
        cooker_devices_path,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    assert len(data) == 1
    assert data[0]["token"] == "token_cooker_1"


@pytest.mark.django_db
def test_deregister_cooker_device_token(
    auth_headers: dict,
    client: APIClient,
    cooker_id: int,
    cooker_devices_path: str,
) -> None:
    CookerFCMDeviceModel.objects.all().delete()

    CookerFCMDeviceModel.objects.create(
        cooker_id=cooker_id,
        token="fcm_token_to_delete",
        device_type="android",
    )

    response = client.post(
        f"{cooker_devices_path}deregister/",
        {"token": "fcm_token_to_delete"},
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("success") is True
    assert CookerFCMDeviceModel.objects.count() == 0
