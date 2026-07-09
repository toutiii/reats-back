import pytest
from core_app.models import CustomerFCMDeviceModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def customer_id() -> int:
    return 1


@pytest.mark.django_db
def test_create_customer_device_token_success(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_devices_path: str,
) -> None:
    # Ensure no device tokens exist initially
    CustomerFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_123456",
        "device_type": "android",
    }

    response = client.post(
        customer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json().get("success") is True

    # Verify database entry
    assert CustomerFCMDeviceModel.objects.count() == 1
    device = CustomerFCMDeviceModel.objects.first()
    assert device is not None
    assert device.token == "fcm_token_123456"
    assert device.device_type == "android"
    assert device.customer.id == customer_id
    assert device.is_active is True


@pytest.mark.django_db
def test_create_customer_device_token_duplicate_overwrites(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_devices_path: str,
) -> None:
    # Ensure no device tokens exist initially
    CustomerFCMDeviceModel.objects.all().delete()

    post_data = {
        "token": "fcm_token_123456",
        "device_type": "android",
    }

    # First POST (creates it for customer 1)
    response = client.post(
        customer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Second POST (updates/overwrites it for customer 1)
    second_request_response = client.post(
        customer_devices_path,
        post_data,
        format="json",
        **auth_headers,
    )
    # Since we use update_or_create, it should return 200 OK and update the token
    assert second_request_response.status_code == status.HTTP_200_OK
    assert CustomerFCMDeviceModel.objects.count() == 1


@pytest.mark.django_db
def test_get_customer_devices_only_returns_own(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_devices_path: str,
) -> None:
    CustomerFCMDeviceModel.objects.all().delete()

    # Create token for current customer (ID 1)
    CustomerFCMDeviceModel.objects.create(
        customer_id=customer_id,
        token="token_customer_1",
        device_type="ios",
    )

    # Create token for another customer (ID 2)
    CustomerFCMDeviceModel.objects.create(
        customer_id=2,
        token="token_customer_2",
        device_type="android",
    )

    response = client.get(
        customer_devices_path,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    assert len(data) == 1
    assert data[0]["token"] == "token_customer_1"


@pytest.mark.django_db
def test_deregister_customer_device_token(
    auth_headers: dict,
    client: APIClient,
    customer_id: int,
    customer_devices_path: str,
) -> None:
    CustomerFCMDeviceModel.objects.all().delete()

    CustomerFCMDeviceModel.objects.create(
        customer_id=customer_id,
        token="fcm_token_to_delete",
        device_type="android",
    )

    response = client.post(
        f"{customer_devices_path}deregister/",
        {"token": "fcm_token_to_delete"},
        format="json",
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("success") is True
    assert CustomerFCMDeviceModel.objects.count() == 0
