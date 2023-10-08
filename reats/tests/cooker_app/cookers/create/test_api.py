from unittest.mock import MagicMock, call

import pytest
from cooker_app.models import CookerModel
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


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
    image: InMemoryUploadedFile,
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
        "photo": image,
    }


@pytest.fixture
def post_data_with_no_profile_pic(
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
    upload_fileobj: MagicMock,
) -> None:
    assert CookerModel.objects.count() == 2

    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert CookerModel.objects.count() == 3

    post_data_keys = list(post_data.keys())
    assert model_to_dict(CookerModel.objects.latest("pk"), fields=post_data_keys) == {
        "firstname": "john",
        "lastname": "Doe",
        "phone": "+33601020304",
        "postal_code": "91100",
        "siret": "12345671234567",
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "town": "test",
        "address_complement": "résidence test",
        "photo": "cookers/+33601020304/profile/test.jpg",
    }

    upload_fileobj.assert_called_once()

    assert len(upload_fileobj.call_args.args) == 3

    arg1, arg2, arg3 = upload_fileobj.call_args.args

    assert isinstance(arg1, InMemoryUploadedFile)
    assert arg1.name == "test.jpg"
    assert arg2 == "reats-dev-bucket"
    assert arg3 == "cookers/+33601020304/profile/test.jpg"


@pytest.mark.django_db
def test_create_cooker_success_with_no_profile_pic(
    client: APIClient,
    path: str,
    post_data_with_no_profile_pic: dict,
) -> None:
    assert CookerModel.objects.count() == 2

    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data_with_no_profile_pic),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert CookerModel.objects.count() == 3

    post_data_keys = list(post_data_with_no_profile_pic.keys()) + [
        "photo",
        "max_order_number",
    ]

    assert model_to_dict(CookerModel.objects.latest("pk"), fields=post_data_keys) == {
        "firstname": "john",
        "lastname": "Doe",
        "phone": "+33601020304",
        "postal_code": "91100",
        "siret": "12345671234567",
        "street_name": "rue du terrier du rat",
        "street_number": "1",
        "town": "test",
        "address_complement": "résidence test",
        "photo": None,
        "max_order_number": 10,
    }


@pytest.mark.django_db
def test_failed_create_cooker_already_exists(
    client: APIClient,
    path: str,
    post_data: dict,
    upload_fileobj: MagicMock,
):
    assert CookerModel.objects.count() == 2

    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert CookerModel.objects.count() == 3
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CookerModel.objects.count() == 3

    upload_fileobj.assert_called_once()

    assert len(upload_fileobj.call_args.args) == 3

    arg1, arg2, arg3 = upload_fileobj.call_args.args

    assert isinstance(arg1, InMemoryUploadedFile)
    assert arg1.name == "test.jpg"
    assert arg2 == "reats-dev-bucket"
    assert arg3 == "cookers/+33601020304/profile/test.jpg"


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
    upload_fileobj: MagicMock,
):
    assert CookerModel.objects.count() == 2
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CookerModel.objects.count() == 2
    upload_fileobj.assert_not_called()
