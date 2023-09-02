import pytest
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.test import APIClient
from source.cooker_app.models import CookerModel


@pytest.fixture
def post_data() -> dict:
    return {
        "firstname": "john",
        "lastname": "Doe",
        "phone": "0601020304",
        "postal_code": "91100",
        "siret": "12345671234567",
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "town": "test",
        "address_complement": "résidence test",
    }


@pytest.fixture(params=["john" * 30])
def invalid_firstname(request) -> str:
    return request.param


@pytest.fixture(params=["Doe" * 30])
def invalid_lastname(request) -> str:
    return request.param


@pytest.fixture(params=["0000000000", "this_is_not_a_phone_number"])
def invalid_phone(request) -> str:
    return request.param


@pytest.fixture(params=["000000", "this_is_not_a_postal_code"])
def invalid_postal_code(request) -> str:
    return request.param


@pytest.fixture(params=["0000000000000000000", "this_is_not_a_siret_number"])
def invalid_siret(request) -> str:
    return request.param


@pytest.fixture(params=["a" * 101])
def invalid_street_name(request) -> str:
    return request.param


@pytest.fixture(params=["9" * 11])
def invalid_street_number(request) -> str:
    return request.param


@pytest.fixture(params=["Evry" * 30])
def invalid_town(request) -> str:
    return request.param


@pytest.fixture(params=["c" * 513])
def invalid_address_complement(request) -> str:
    return request.param


@pytest.fixture
def invalid_post_data(
    invalid_address_complement: str,
    invalid_firstname: str,
    invalid_lastname: str,
    invalid_phone: str,
    invalid_postal_code: str,
    invalid_siret: str,
    invalid_street_name: str,
    invalid_street_number: str,
    invalid_town: str,
) -> dict:
    return {
        "firstname": invalid_firstname,
        "lastname": invalid_lastname,
        "phone": invalid_phone,
        "postal_code": invalid_postal_code,
        "siret": invalid_siret,
        "street_name": invalid_street_name,
        "street_number": invalid_street_number,
        "town": invalid_town,
        "address_complement": invalid_address_complement,
    }


@pytest.fixture
def path() -> str:
    return "/api/v1/cookers/"


@pytest.mark.django_db
def test_success_create_cooker(
    client: APIClient,
    path: str,
    post_data: dict,
):
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


@pytest.mark.django_db
def test_failed_create_cooker_wrong_data(
    client: APIClient,
    path: str,
    invalid_post_data: dict,
):
    response = client.post(path, invalid_post_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
