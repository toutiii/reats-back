from unittest.mock import ANY, MagicMock, patch

import pytest
from customer_app.models import CustomerModel
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
    }


@pytest.mark.django_db
@patch("stripe.Customer.list")
@pytest.mark.parametrize(
    "customer_data_returned_by_stripe",
    [
        [],
        [
            {
                "address": None,
                "balance": 0,
                "created": 1727626679,
                "currency": None,
                "default_source": None,
                "delinquent": False,
                "description": None,
                "discount": None,
                "email": "+33601020304@customer-app.com",
                "id": "cus_QwIPjeUXejXa55",
                "invoice_prefix": "8BC7CAC1",
                "invoice_settings": {
                    "custom_fields": None,
                    "default_payment_method": None,
                    "footer": None,
                    "rendering_options": None,
                },
                "livemode": False,
                "metadata": {},
                "name": "John DOE",
                "object": "customer",
                "phone": "+33601020304",
                "preferred_locales": ["fr"],
                "shipping": None,
                "tax_exempt": "none",
                "test_clock": None,
            }
        ],
    ],
    ids=[
        "customer not found ins stripe",
        "customer found in stripe",
    ],
)
def test_create_customer_success(
    mock_stripe_customer_list: MagicMock,
    customer_api_key_header: dict,
    send_otp_message_success: MagicMock,
    mock_stripe_customer_create: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
    customer_data_returned_by_stripe: list,
) -> None:
    mock_stripe_customer_list.return_value.data = customer_data_returned_by_stripe
    mock_stripe_customer_list.return_value.has_more = False
    mock_stripe_customer_list.return_value.object = "list"
    mock_stripe_customer_list.return_value.url = "/v1/customers"
    old_count = CustomerModel.objects.count()
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **customer_api_key_header
    )
    assert response.status_code == status.HTTP_201_CREATED
    new_count = CustomerModel.objects.count()

    assert new_count - old_count == 1

    post_data_keys = list(post_data.keys()) + ["photo"]

    assert model_to_dict(CustomerModel.objects.latest("pk"), fields=post_data_keys) == {
        "firstname": "John",
        "lastname": "DOE",
        "phone": "+33601020304",
        "photo": "customers/1/profile_pics/default-profile-pic.jpg",
    }
    assert CustomerModel.objects.latest("pk").is_activated is False
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
    mock_stripe_customer_list.assert_called_once_with(
        email="+33601020304@customer-app.com",
    )

    if customer_data_returned_by_stripe:
        mock_stripe_customer_create.assert_not_called()
    else:
        assert CustomerModel.objects.latest("pk").stripe_id == "cus_QwIHcNB1jkYFwv"
        mock_stripe_customer_create.assert_called_once_with(
            name="John DOE",
            phone="+33601020304",
            preferred_locales=["fr"],
            email="+33601020304@customer-app.com",
        )


class TestActivateCustomerSuccess:
    @pytest.fixture
    def otp_data(self, otp: str, post_data: dict) -> dict:
        return {"phone": post_data["phone"], "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        customer_api_key_header: dict,
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
            **customer_api_key_header
        )

        assert create_response.status_code == status.HTTP_201_CREATED

        user = CustomerModel.objects.latest("pk")

        assert user.is_activated is False

        activate_response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header
        )

        assert activate_response.status_code == status.HTTP_200_OK

        user = CustomerModel.objects.latest("pk")

        assert user.is_activated is True

        verify_otp_message_success.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": "+33601020304",
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestActivateCustomerFailedInCaseOfFailingOTPValidation:
    @pytest.fixture
    def otp_data(self, otp: str, post_data: dict) -> dict:
        return {"phone": post_data["phone"], "otp": otp}

    @pytest.mark.django_db
    def test_response(
        self,
        customer_api_key_header: dict,
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
            **customer_api_key_header
        )

        assert create_response.status_code == status.HTTP_201_CREATED

        user = CustomerModel.objects.latest("pk")

        assert user.is_activated is False

        activate_response = client.post(
            otp_verify_path,
            encode_multipart(BOUNDARY, otp_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header
        )

        assert activate_response.status_code == status.HTTP_400_BAD_REQUEST

        user = CustomerModel.objects.latest("pk")

        assert user.is_activated is False

        verify_otp_message_failed.assert_called_once_with(
            ApplicationId="41db7f0c9f8d4a43b7e649b37b429da8",
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": "+33601020304",
                "ReferenceId": ANY,
                "Otp": "002233",
            },
        )


class TestCreateSameCustomerTwice:
    @pytest.fixture
    def e164_phone(self) -> str:
        return "+33700000010"

    @pytest.fixture
    def phone(self) -> str:
        return "0700000010"

    @pytest.mark.django_db(transaction=True)
    def test_response(
        self,
        customer_api_key_header: dict,
        send_otp_message_success: MagicMock,
        client: APIClient,
        path: str,
        post_data: dict,
    ) -> None:
        old_count = CustomerModel.objects.count()

        create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        new_count = CustomerModel.objects.count()

        assert new_count - old_count == 1

        duplicate_create_response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **customer_api_key_header
        )
        assert duplicate_create_response.status_code == status.HTTP_400_BAD_REQUEST
        assert CustomerModel.objects.count() == new_count

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
def test_failed_create_customer_wrong_data(
    customer_api_key_header: dict,
    send_otp_message_success: MagicMock,
    client: APIClient,
    path: str,
    post_data: dict,
    upload_fileobj: MagicMock,
) -> None:
    old_count = CustomerModel.objects.count()
    response = client.post(
        path,
        encode_multipart(BOUNDARY, post_data),
        content_type=MULTIPART_CONTENT,
        follow=False,
        **customer_api_key_header
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    new_count = CustomerModel.objects.count()
    assert old_count == new_count
    upload_fileobj.assert_not_called()
    send_otp_message_success.assert_not_called()
