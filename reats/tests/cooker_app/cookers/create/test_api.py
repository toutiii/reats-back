from unittest.mock import ANY, MagicMock

import pytest
from cooker_app.models import CookerModel
from django.core.files.uploadedfile import InMemoryUploadedFile
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
    send_otp_message_success: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
) -> None:
    old_count = CookerModel.objects.count()

    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_201_CREATED
    new_count = CookerModel.objects.count()

    assert new_count - old_count == 1

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
    def e164_phone(self) -> str:
        return "+33700000000"

    @pytest.fixture
    def phone(self) -> str:
        return "0700000000"

    @pytest.mark.django_db
    def test_response(
        self,
        send_otp_message_success: MagicMock,
        client: APIClient,
        path: str,
        post_data: dict,
    ) -> None:
        old_count = CookerModel.objects.count()

        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_201_CREATED
        new_count = CookerModel.objects.count()

        assert new_count - old_count == 1

        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CookerModel.objects.count() == new_count

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
                "DestinationIdentity": "+33700000000",
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
    send_otp_message_success: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
    upload_fileobj: MagicMock,
) -> None:
    old_count = CookerModel.objects.count()
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    new_count = CookerModel.objects.count()
    assert old_count == new_count
    upload_fileobj.assert_not_called()
    send_otp_message_success.assert_not_called()


class TestCookerAuth:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33600000003"

    @pytest.fixture
    def auth_data(self) -> dict:
        return {"phone": "0600000003"}

    @pytest.mark.parametrize(
        "auth_data",
        [
            {},
            {"phone": "this_is_not_a_phone_number"},
            {"phone": "0600000000"},
            {"phone": "0600000002"},
        ],
        ids=[
            "missing_phone_number",
            "invalid_phone_number",
            "unknown_user",
            "known_but_non_activated_user",
        ],
    )
    @pytest.mark.django_db
    def test_cooker_auth_failed(
        self,
        auth_data: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, auth_data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_cooker_auth_success(
        self,
        auth_data: dict,
        client: APIClient,
        auth_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            auth_path,
            encode_multipart(BOUNDARY, auth_data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_200_OK
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
                "DestinationIdentity": "+33600000003",
                "ReferenceId": ANY,
            },
        )


class TestCookerAskNewOTP:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33600000003"

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "0600000003"}

    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"phone": "this_is_not_a_phone_number"},
        ],
        ids=[
            "missing_phone_number",
            "invalid_phone_number",
        ],
    )
    @pytest.mark.django_db
    def test_cooker_ask_new_OTP_failed(
        self,
        data: dict,
        client: APIClient,
        otp_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        send_otp_message_success.assert_not_called()

    @pytest.mark.django_db
    def test_cooker_ask_new_OTP_success(
        self,
        data: dict,
        client: APIClient,
        otp_path: str,
        send_otp_message_success: MagicMock,
    ) -> None:
        response = client.post(
            otp_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_200_OK
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
                "DestinationIdentity": "+33600000003",
                "ReferenceId": ANY,
            },
        )


class TestTokenFetch:
    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"unexpected_field": "test_data"},
            {"username": "test", "password": "test"},
        ],
        ids=[
            "missing_field",
            "invalid_field",
            "deprecated_fields",
        ],
    )
    def test_fetch_token_failed_with_missing_phone_field(
        self,
        client: APIClient,
        data: dict,
        token_path: str,
        ssm_get_parameter: MagicMock,
    ) -> None:
        response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        ssm_get_parameter.assert_not_called()

    @pytest.fixture
    def data(self) -> dict:
        return {"phone": "0600000003"}

    @pytest.mark.django_db
    def test_fetch_token_success(
        self,
        client: APIClient,
        data: dict,
        token_path: str,
        ssm_get_parameter: MagicMock,
    ) -> None:
        response = client.post(
            token_path,
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "ok": True,
            "token": {
                "access": ANY,
                "refresh": ANY,
            },
            "user_id": ANY,
        }
        ssm_get_parameter.assert_not_called()
