from unittest.mock import ANY, MagicMock

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
    admin_create_user: MagicMock,
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
        "photo": "cookers/1/profile_pics/default-profile-pic.jpg",
        "max_order_number": 10,
    }
    assert CookerModel.objects.latest("pk").is_online is False
    admin_create_user.assert_called_once_with(
        UserPoolId=ANY,
        Username="+33601020304",
        UserAttributes=[
            {"Name": "given_name", "Value": "john"},
            {"Name": "family_name", "Value": "Doe"},
        ],
        TemporaryPassword=ANY,
        DesiredDeliveryMediums=["SMS"],
    )


class TestFailedCreateCookerAlreadyExists:
    @pytest.fixture
    def phone(self) -> str:
        return "0600000002"

    @pytest.mark.django_db
    def test_response(
        self,
        admin_create_user: MagicMock,
        client: APIClient,
        path: str,
        post_data: dict,
    ):
        assert CookerModel.objects.count() == 2

        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CookerModel.objects.count() == 2
        admin_create_user.assert_not_called()


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
    admin_create_user: MagicMock,
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
    admin_create_user.assert_not_called()
