import pytest
from delivery_app.models import DeliverModel
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def e164_phone() -> str:
    return "+33601020304"


@pytest.fixture
def data(e164_phone: str) -> dict:
    return {"phone": e164_phone}


@pytest.fixture
def phone() -> str:
    return "0601020304"


@pytest.fixture
def otp() -> str:
    return "002233"


@pytest.fixture
def post_data(phone: str) -> dict:
    return {
        "firstname": "John",
        "lastname": "DOE",
        "phone": phone,
        "delivery_vehicile": "bike",
        "max_capacity_per_delivery": 5,
        "delivery_postal_code": "91100",
        "delivery_town": "Corbeil-Essonnes",
        "delivery_radius": 10,
    }


@pytest.mark.django_db
def test_delete_deliver_success(
    data: dict,
    delivery_api_key_header: dict,
    e164_phone: str,
    token_path: str,
    client: APIClient,
    path: str,
    post_data: dict,
) -> None:
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **delivery_api_key_header,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_deliver = DeliverModel.objects.get(phone=e164_phone)

    post_data_keys = list(post_data.keys()) + ["photo", "is_activated", "is_enabled"]

    assert model_to_dict(created_deliver, fields=post_data_keys) == {
        "firstname": "John",
        "lastname": "DOE",
        "phone": "+33601020304",
        "photo": "delivers/1/profile_pics/default-profile-pic.jpg",
        "delivery_vehicile": "bike",
        "max_capacity_per_delivery": 5,
        "delivery_postal_code": "91100",
        "delivery_town": "Corbeil-Essonnes",
        "delivery_radius": 10,
        "is_activated": False,
        "is_enabled": True,
    }

    with freeze_time("2024-01-20T17:05:45+00:00"):
        token_response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header,
        )

        assert token_response.status_code == status.HTTP_200_OK
        access_token = token_response.json().get("token").get("access")
        access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        response = client.delete(
            f"{path}{created_deliver.pk}/",
            follow=False,
            **access_auth_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "status_code": status.HTTP_200_OK,
        }
        created_deliver = DeliverModel.objects.get(phone=e164_phone)
        assert model_to_dict(created_deliver, fields=post_data_keys) == {
            "firstname": "John",
            "lastname": "DOE",
            "phone": "+33601020304",
            "photo": "delivers/1/profile_pics/default-profile-pic.jpg",
            "delivery_vehicile": "bike",
            "max_capacity_per_delivery": 5,
            "delivery_postal_code": "91100",
            "delivery_town": "Corbeil-Essonnes",
            "delivery_radius": 10,
            "is_activated": False,
            "is_enabled": False,
        }
