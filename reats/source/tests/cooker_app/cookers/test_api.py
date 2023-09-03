import pytest
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.test import APIClient
from source.cooker_app.models import CookerModel


@pytest.fixture
def path() -> str:
    return "/api/v1/cookers/"


@pytest.fixture
def phone() -> str:
    return "0601020304"


@pytest.fixture
def postal_code() -> str:
    return "91100"


@pytest.fixture
def siret() -> str:
    return "12345671234567"


@pytest.fixture
def post_data(
    phone: str,
    postal_code: str,
    siret: str,
) -> dict:
    return {
        "firstname": "john",
        "lastname": "Doe",
        "phone": phone,
        "postal_code": postal_code,
        "siret": siret,
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "town": "test",
        "address_complement": "résidence test",
    }


@pytest.mark.django_db
def test_create_cooker_success(
    client: APIClient,
    path: str,
    post_data: dict,
) -> None:
    response = client.post(path, post_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert CookerModel.objects.count() == 1

    post_data_keys = list(post_data.keys())
    assert model_to_dict(
        CookerModel.objects.latest("created"), fields=post_data_keys
    ) == {
        "firstname": "john",
        "lastname": "Doe",
        "phone": "+33 6 01 02 03 04",
        "postal_code": "91100",
        "siret": "12345671234567",
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "town": "test",
        "address_complement": "résidence test",
    }


@pytest.mark.django_db
def test_failed_create_cooker_already_exists(
    client: APIClient,
    path: str,
    post_data: dict,
):
    response = client.post(path, post_data)
    response = client.post(path, post_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CookerModel.objects.count() == 1


@pytest.mark.parametrize(
    "phone,postal_code,siret",
    [
        (
            "0000000000",
            "000000",
            "0000000000000000000",
        ),
        (
            "this_is_not_a_phone_number",
            "this_is_not_a_postal_code",
            "this_is_not_a_siret_number",
        ),
    ],
)
@pytest.mark.django_db
def test_failed_create_cooker_wrong_data(
    client: APIClient,
    path: str,
    post_data: dict,
):
    response = client.post(path, post_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CookerModel.objects.count() == 0
