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
def otp() -> str:
    return "002233"


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


@pytest.mark.django_db(transaction=True)
def test_create_cooker_success(
    send_otp_message: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
) -> None:
    assert CookerModel.objects.count() == 2

    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert CookerModel.objects.count() == 3

    post_data_keys = list(post_data.keys()) + [
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
    assert CookerModel.objects.latest("pk").is_activated is False
    send_otp_message.assert_called_once_with(
        ApplicationId=ANY,
        SendOTPMessageRequestParameters={
            "Channel": "SMS",
            "BrandName": ANY,
            "CodeLength": 6,
            "ValidityPeriod": 30,
            "AllowedAttempts": 3,
            "Language": "fr-FR",
            "OriginationIdentity": ANY,
            "DestinationIdentity": "+33601020304",
            "ReferenceId": ANY,
        },
    )


class TestActivateCookerSuccessful:
    @pytest.fixture
    def otp_data(self, otp: str) -> dict:
        return {"phone": "0600000002", "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        client: APIClient,
        otp_data: dict,
        otp_verify_path: str,
        verify_otp_message_success: MagicMock,
    ) -> None:
        phone = "+33600000002"
        user = CookerModel.objects.get(phone=phone)
        assert user.is_activated is False

        response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
        )

        assert response.status_code == status.HTTP_200_OK

        user = CookerModel.objects.get(phone=phone)
        assert user.is_activated is True
        verify_otp_message_success.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": phone,
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestActivateCookerFailed:
    @pytest.fixture
    def otp_data(self, otp: str) -> dict:
        return {"phone": "0600000002", "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        client: APIClient,
        otp_data: dict,
        otp_verify_path: str,
        verify_otp_message_failed: MagicMock,
    ) -> None:
        phone = "+33600000002"
        user = CookerModel.objects.get(phone=phone)
        assert user.is_activated is False

        response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        user = CookerModel.objects.get(phone=phone)
        assert user.is_activated is False
        verify_otp_message_failed.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": phone,
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestCreateSameCookerTwice:
    @pytest.fixture
    def phone(self) -> str:
        return "0600000003"

    @pytest.mark.django_db
    def test_response(
        self,
        send_otp_message: MagicMock,
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
        assert response.status_code == status.HTTP_201_CREATED
        assert CookerModel.objects.count() == 3

        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CookerModel.objects.count() == 3

        send_otp_message.assert_called_once_with(
            ApplicationId=ANY,
            SendOTPMessageRequestParameters={
                "Channel": "SMS",
                "BrandName": ANY,
                "CodeLength": 6,
                "ValidityPeriod": 30,
                "AllowedAttempts": 3,
                "Language": "fr-FR",
                "OriginationIdentity": ANY,
                "DestinationIdentity": "+33600000003",
                "ReferenceId": ANY,
            },
        )


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
    send_otp_message: MagicMock,
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
    send_otp_message.assert_not_called()
