from unittest.mock import ANY, MagicMock

import pytest
from delivery_app.models import DeliverModel
from django.forms.models import model_to_dict
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def e164_phone() -> str:
    return "+33601020304"


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
        "delivery_vehicle": "bike",
        "town": "Corbeil-Essonnes",
        "delivery_radius": 10,
        "siret": "12345678901234",
    }


@pytest.mark.django_db
def test_create_deliver_success(
    delivery_api_key_header: dict,
    send_otp_message_success: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
) -> None:
    old_count = DeliverModel.objects.count()
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **delivery_api_key_header
    )
    assert response.status_code == status.HTTP_201_CREATED
    new_count = DeliverModel.objects.count()

    assert new_count - old_count == 1

    post_data_keys = list(post_data.keys()) + [
        "photo",
        "is_activated",
        "is_deleted",
        "is_online",
    ]

    assert model_to_dict(DeliverModel.objects.latest("pk"), fields=post_data_keys) == {
        "firstname": "John",
        "lastname": "DOE",
        "phone": "+33601020304",
        "photo": "delivers/1/profile_pics/default-profile-pic.jpg",
        "delivery_vehicle": "bike",
        "town": "Corbeil-Essonnes",
        "delivery_radius": 10,
        "is_activated": False,
        "siret": "12345678901234",
        "is_deleted": False,
        "is_online": False,
    }
    assert DeliverModel.objects.latest("pk").is_activated is False
    send_otp_message_success.assert_called_once_with(
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


class TestActivateDeliverSuccess:
    @pytest.fixture
    def otp_data(self, otp: str, post_data: dict) -> dict:
        return {"phone": post_data["phone"], "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        delivery_api_key_header: dict,
        client: APIClient,
        otp_data: dict,
        otp_verify_path: str,
        path: str,
        post_data: dict,
        verify_otp_message_success: MagicMock,
    ) -> None:
        create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )

        assert create_response.status_code == status.HTTP_201_CREATED

        user = DeliverModel.objects.latest("pk")

        assert user.is_activated is False

        activate_response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )

        assert activate_response.status_code == status.HTTP_200_OK

        user = DeliverModel.objects.latest("pk")

        assert user.is_activated is True

        verify_otp_message_success.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": "+33601020304",
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestActivateDeliverFailedInCaseOfFailingOTPValidation:
    @pytest.fixture
    def otp_data(self, otp: str, post_data: dict) -> dict:
        return {"phone": post_data["phone"], "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        delivery_api_key_header: dict,
        client: APIClient,
        otp_data: dict,
        otp_verify_path: str,
        path: str,
        post_data: dict,
        verify_otp_message_failed: MagicMock,
    ) -> None:
        create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )

        assert create_response.status_code == status.HTTP_201_CREATED

        user = DeliverModel.objects.latest("pk")

        assert user.is_activated is False

        activate_response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )

        assert activate_response.status_code == status.HTTP_400_BAD_REQUEST

        user = DeliverModel.objects.latest("pk")

        assert user.is_activated is False

        verify_otp_message_failed.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": "+33601020304",
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestCreateSameDeliverTwice:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33700000010"

    @pytest.fixture
    def phone(self) -> str:
        return "0700000010"

    @pytest.mark.django_db(transaction=True)
    def test_response(
        self,
        delivery_api_key_header: dict,
        send_otp_message_success: MagicMock,
        client: APIClient,
        path: str,
        post_data: dict,
    ) -> None:
        old_count = DeliverModel.objects.count()

        create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        new_count = DeliverModel.objects.count()

        assert new_count - old_count == 1

        duplicate_create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **delivery_api_key_header
        )
        assert duplicate_create_response.status_code == status.HTTP_400_BAD_REQUEST
        assert DeliverModel.objects.count() == new_count

        send_otp_message_success.assert_called_once_with(
            ApplicationId=ANY,
            SendOTPMessageRequestParameters={
                "Channel": "SMS",
                "BrandName": ANY,
                "CodeLength": 6,
                "ValidityPeriod": 30,
                "AllowedAttempts": 3,
                "Language": "fr-FR",
                "OriginationIdentity": ANY,
                "DestinationIdentity": "+33700000010",
                "ReferenceId": ANY,
            },
        )


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "0000000000",
        "000000",
        "0000000000000000000",
        "this_is_not_a_phone_number",
    ],
)
@pytest.mark.django_db
def test_failed_create_deliver_wrong_data(
    delivery_api_key_header: dict,
    send_otp_message_success: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
    upload_fileobj: MagicMock,
) -> None:
    old_count = DeliverModel.objects.count()
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **delivery_api_key_header
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    new_count = DeliverModel.objects.count()
    assert old_count == new_count
    upload_fileobj.assert_not_called()
    send_otp_message_success.assert_not_called()
