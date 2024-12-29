import json
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Iterator
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
import stripe
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import call_command
from PIL import Image
from rest_framework.test import APIClient


@pytest.fixture(scope="session")
def client():
    return APIClient()


@pytest.fixture(scope="session")
def image() -> InMemoryUploadedFile:
    im = Image.new(mode="RGB", size=(200, 200))  # create a new image using PIL
    im_io = BytesIO()  # a BytesIO object for saving image
    im.save(im_io, "JPEG")  # save the image to im_io
    im_io.seek(0)  # seek to the beginning

    image = InMemoryUploadedFile(
        im_io, None, "test.jpg", "image/jpeg", len(im_io.getvalue()), None
    )

    return image


@pytest.fixture
def upload_fileobj() -> Iterator:
    patcher = patch("utils.common.s3.upload_fileobj")
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def delete_object() -> Iterator:
    patcher = patch("utils.common.s3.delete_object")
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def send_otp_message_success(e164_phone: str) -> Iterator:
    patcher = patch(
        "utils.common.pinpoint_client.send_otp_message",
        return_value={
            "MessageResponse": {
                "ApplicationId": "41db7f0c9f8d4a43b7e649b37b429da8",
                "RequestId": "QZ9kmHgvFiAEYBQ=",
                "Result": {
                    e164_phone: {
                        "DeliveryStatus": "SUCCESSFUL",
                        "MessageId": "6n10pvt1aq8h9tvnug6feqeo4drva73lqidg3e80",
                        "StatusCode": 200,
                        "StatusMessage": "MessageId: 6n10pvt1aq8h9tvnug6feqeo4drva73lqidg3e80",
                    }
                },
            },
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def send_otp_message_failed(e164_phone: str) -> Iterator:
    patcher = patch(
        "utils.common.pinpoint_client.send_otp_message",
        return_value={
            "MessageResponse": {
                "ApplicationId": "41db7f0c9f8d4a43b7e649b37b429da8",
                "RequestId": "QZ9kmHgvFiAEYBQ=",
                "Result": {
                    e164_phone: {
                        "DeliveryStatus": "SUCCESSFUL",
                        "MessageId": "6n10pvt1aq8h9tvnug6feqeo4drva73lqidg3e80",
                        "StatusCode": 400,
                        "StatusMessage": "MessageId: 6n10pvt1aq8h9tvnug6feqeo4drva73lqidg3e80",
                    }
                },
            },
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def verify_otp_message_success() -> Iterator:
    patcher = patch(
        "utils.common.pinpoint_client.verify_otp_message",
        return_value={
            "VerificationResponse": {
                "Valid": True,
            }
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def verify_otp_message_failed() -> Iterator:
    patcher = patch(
        "utils.common.pinpoint_client.verify_otp_message",
        return_value={
            "VerificationResponse": {
                "Valid": False,
            }
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def ssm_get_parameter() -> Iterator:
    patcher = patch("source.settings.ssm_client.get_parameter")
    yield patcher.start()
    patcher.stop()


@pytest.fixture(scope="session")
def private_key() -> str:
    return """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9qhxW7K+C8gKX
anN2V48KwHax/xXGRdso3sZSIqXBOe2NwiGi9LLrhueg0gMBmJKSCdlVrndnB/ap
dMn1M2e8w25GNijxR6C7/TnNNhfxe7mUn5LmM9PQmOhbYujd2Y8v4tq/ype1uFv3
cHWUTydhfO3gPUGaYgZegWdcAB7M/WUHNeM4a4DlRL21iz2wZ/Wex9vVn+OaCVwk
Np1Xf9vpCKPIOsubUB+HH61NvjBxYz75+Ea0YhXVsGigEkF6BJvVGtcsHq1XBH+B
5XNR3lVcKVFSsb6TZFztnWu6gRP5zr+W3oRxsIDiOAoX1XbmNM7iHqOvBkwXe94x
MLkHmgEhAgMBAAECggEAA+z79i6i+V5iAFlTN31beBkAu/FwNXDntuJZj4SpEqVM
zfTZNmLDO03JCJKgPk22pvAuP/BDB25qRBqnPXyJZqZS54Aie9AEOy/kHOPEPhrV
/gYJh9tFxJkNoiqbcFAa/x4+cd7TIg9FVAtPW7kBsypfUBdkfroNsLIT/hsAiDSj
Xa+OYTBTLz7+xmf474hDF5sq/Jg6q9bEX5jpvR4W7OIy5fWEoovfTTNSan/jjMzT
jjyH/CG1AdCmSJn/2QVBLrCYc3oPYuJKtDVnU4eXd7gzeKVHcR8Eq6bpVk55VTJ/
4k/jm6x8V6VUzDDQ5e4zsownzIFPOBY7Ef1JcGTiewKBgQDYxIQYgYjGfX+WfvM9
0n5QwIJy/Yaosimaca2Or90D89cXdA4zqovqjEtCYtdfMyp8nGect/1c/lqQ9vTG
zHrO6pvTTSk0gaq3a6g3dU+EqjZTh8YFkXuG0y4F3XfPIETipC4NIURJu8P5HFe7
fEhoAQUxsaNU6M8NDCsPv3hdowKBgQDf/dN3WQ1/UoFN00eiWs8CyCRFgPaMtBTv
lQp012o4Hb7Aq0jiSM2r9GPS15g0qdDlRFq+DdBcdUPlM30TcZmdXmmpvjazcRs0
OVIs3u6vnDblGWGoIsEmXzVeRgAvHVIs0AHqC21wZvaT2zLLB/VXi7sdISD3G4eD
0mOoZfuKawKBgGuO/1jFlZ+gEBoV/g5UDxd0noX+ZL36QYiAFbVycAGREc5yaMWc
P3bvjDxxnRqA4fkZBpSN+ysUjs3VrFmkht97LDzp0aNbH+GJituR2xYh+3jxKwIC
UT/yM6j3XoapJWUsQCmFs0O+5pwKQ0IlhiwNLY2d7kSojGyV+BwFTu1vAoGBANIY
Q+Q7DDTzj0MPPK6lHGyQi60BpMAfHVAHbNJhR0kxZT1Uq71L6lYymfsmq6Yh7kVN
kwuW62v9tdxjKhs1v49jAhrrxmUTXx/h8BkUVa80CC1lXDsXtjGmtekiIYQPrYdI
57K+Wz1F5lyTCpZzdYVTFAPjkgcVtEtJ6J4IYiLXAoGAYxcoQpt82znym2MXxiK5
Ze0c/lpxdfVVr+WwdKtGrb8SLaGnkHZAgThTxgMf48Zm1L6CxwcLnCcSgN24gCVU
uuDw5Qp3KSOx8jG6GJMGmgLoRxVL4zx0Kl2zmXssYYDg/J6BZq3xFjm9DYIZnGHe
qKd7cN3OExYGF87+5QblDQk=
-----END PRIVATE KEY-----"""


@pytest.fixture(scope="session")
def public_key() -> str:
    return """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvaocVuyvgvICl2pzdleP
CsB2sf8VxkXbKN7GUiKlwTntjcIhovSy64bnoNIDAZiSkgnZVa53Zwf2qXTJ9TNn
vMNuRjYo8Uegu/05zTYX8Xu5lJ+S5jPT0JjoW2Lo3dmPL+Lav8qXtbhb93B1lE8n
YXzt4D1BmmIGXoFnXAAezP1lBzXjOGuA5US9tYs9sGf1nsfb1Z/jmglcJDadV3/b
6QijyDrLm1Afhx+tTb4wcWM++fhGtGIV1bBooBJBegSb1RrXLB6tVwR/geVzUd5V
XClRUrG+k2Rc7Z1ruoET+c6/lt6EcbCA4jgKF9V25jTO4h6jrwZMF3veMTC5B5oB
IQIDAQAB
-----END PUBLIC KEY-----"""


@pytest.fixture(scope="session")
def token_with_bearer(private_key: str) -> str:
    due_date = datetime.now(timezone.utc) + timedelta(minutes=60)
    payload = {
        "exp": int(due_date.timestamp()),
        "jti": str(uuid4()),
        "user_id": 1,
        "token_type": "access",
    }
    secret = load_pem_private_key(private_key.encode(), None)
    assert isinstance(secret, rsa.RSAPrivateKey)

    test_token = jwt.encode(
        payload,
        secret,
        algorithm=os.getenv("DJANGO_SIMPLE_JWT_ALGORITHM"),
    )

    return f"Bearer {test_token}"


@pytest.fixture(autouse=True)
def simple_jwt_overload(settings, private_key: str, public_key: str) -> None:
    settings.SIMPLE_JWT = {
        "ALGORITHM": os.getenv("DJANGO_SIMPLE_JWT_ALGORITHM"),
        "SIGNING_KEY": private_key,
        "VERIFYING_KEY": public_key,
        "TOKEN_OBTAIN_SERIALIZER": "cookers_app.serializers.TokenObtainPairWithoutPasswordSerializer",
    }


@pytest.fixture(autouse=True, scope="session")
def auth_headers(token_with_bearer: str) -> dict:
    return {"HTTP_AUTHORIZATION": token_with_bearer}


@pytest.fixture(autouse=True)
def customer_app_api_key(settings) -> None:
    settings.CUSTOMER_APP_API_KEY = "some-api-key-for-customer-app"


@pytest.fixture
def customer_api_key_header(settings) -> dict:
    return {
        "HTTP_X-Api-Key": settings.CUSTOMER_APP_API_KEY,
        "HTTP_App-Origin": "customer",
    }


@pytest.fixture(autouse=True)
def cooker_app_api_key(settings) -> None:
    settings.COOKER_APP_API_KEY = "some-api-key-for-cooker-app"


@pytest.fixture
def cooker_api_key_header(settings) -> dict:
    return {
        "HTTP_X-Api-Key": settings.COOKER_APP_API_KEY,
        "HTTP_App-Origin": "cooker",
    }


@pytest.fixture(autouse=True)
def delivery_app_api_key(settings) -> None:
    settings.DELIVERY_APP_API_KEY = "some-api-key-for-delivery-app"


@pytest.fixture
def delivery_api_key_header(settings) -> dict:
    return {
        "HTTP_X-Api-Key": settings.DELIVERY_APP_API_KEY,
        "HTTP_App-Origin": "delivery",
    }


@pytest.fixture(autouse=True, scope="session")
def mock_get_pre_signed_url() -> Iterator:
    patcher = patch(
        "utils.common.get_pre_signed_url",
        return_value="https://some-url.com",
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    fixtures = [
        "customers",
        "addresses",
        "cookers",
        "delivers",
        "dishes",
        "drinks",
        "orders",
        "order_items",
    ]

    with django_db_blocker.unblock():
        call_command("loaddata", *fixtures)


@pytest.fixture(autouse=True)
def mock_googlemaps_distance_matrix() -> Iterator:
    patcher = patch(
        "utils.distance_computer.google_map_client.distance_matrix",
        return_value={
            "destination_addresses": [
                "1 Rue André Lalande, 91000 Évry-Courcouronnes, " "France"
            ],
            "origin_addresses": [
                "13 Rue des Mazières, 91000 Évry-Courcouronnes, France"
            ],
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "1.4 km", "value": 1390},
                            "duration": {"text": "5 mins", "value": 325},
                            "status": "OK",
                        }
                    ]
                }
            ],
            "status": "OK",
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_payment_intent_create() -> Iterator:
    patcher = patch(
        "stripe.PaymentIntent.create",
        return_value=stripe.util.convert_to_dict(
            json.loads(
                """{
                "amount": 150870,
                "amount_capturable": 0,
                "amount_details": {"tip": {}},
                "amount_received": 0,
                "application": null,
                "application_fee_amount": null,
                "automatic_payment_methods": {
                    "allow_redirects": "always",
                    "enabled": true
                },
                "canceled_at": null,
                "cancellation_reason": null,
                "capture_method": "automatic_async",
                "client_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "confirmation_method": "automatic",
                "created": 1728125115,
                "currency": "eur",
                "customer": "cus_QyZ76Ae0W5KeqP",
                "description": null,
                "id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "invoice": null,
                "last_payment_error": null,
                "latest_charge": null,
                "livemode": false,
                "metadata": {},
                "next_action": null,
                "object": "payment_intent",
                "on_behalf_of": null,
                "payment_method": null,
                "payment_method_configuration_details": null,
                "payment_method_options": {
                    "card": {
                        "installments": null,
                        "mandate_options": null,
                        "network": null,
                        "request_three_d_secure": "automatic"
                    }
                },
                "payment_method_types": ["card"],
                "processing": null,
                "receipt_email": null,
                "review": null,
                "setup_future_usage": null,
                "shipping": null,
                "source": null,
                "statement_descriptor": null,
                "statement_descriptor_suffix": null,
                "status": "requires_payment_method",
                "transfer_data": null,
                "transfer_group": null
            }"""
            )
        ),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_create_ephemeral_key() -> Iterator:
    patcher = patch(
        "stripe.EphemeralKey.create",
        return_value=stripe.util.convert_to_dict(
            json.loads(
                """{
                "associated_objects": [
                    {
                    "id": "cus_QyZ76Ae0W5KeqP",
                    "type": "customer"
                    }
                ],
                "created": 1728745953,
                "expires": 1728749553,
                "id": "ephkey_1Q96zdEEYeaFww1WqdVzrVXX",
                "livemode": false,
                "object": "ephemeral_key",
                "secret": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp"
                }
                """
            )
        ),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_payment_intent_update() -> Iterator:
    patcher = patch("stripe.PaymentIntent.modify", return_value=None)
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def stripe_payment_intent_success_webhook_data() -> dict:
    return {
        "id": "evt_3QJJlHEEYeaFww1W0AkpYuqj",
        "object": "event",
        "api_version": "2024-06-20",
        "created": 1731178320,
        "data": {
            "object": {
                "id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "object": "payment_intent",
                "amount": 2313,
                "amount_capturable": 0,
                "amount_details": {"tip": {}},
                "amount_received": 2313,
                "application": None,
                "application_fee_amount": None,
                "automatic_payment_methods": {
                    "allow_redirects": "always",
                    "enabled": True,
                },
                "canceled_at": None,
                "cancellation_reason": None,
                "capture_method": "automatic_async",
                "client_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "confirmation_method": "automatic",
                "created": 1731178315,
                "currency": "eur",
                "customer": "cus_QyZ76Ae0W5KeqP",
                "description": None,
                "invoice": None,
                "last_payment_error": None,
                "latest_charge": "ch_3QJJlHEEYeaFww1W0GkaBZRx",
                "livemode": False,
                "metadata": {},
                "next_action": None,
                "on_behalf_of": None,
                "payment_method": "pm_1QJIFdEEYeaFww1Wv5PfwHlU",
                "payment_method_configuration_details": {
                    "id": "pmc_1QJHuCEEYeaFww1WIyoetNa8",
                    "parent": None,
                },
                "payment_method_options": {
                    "card": {
                        "installments": None,
                        "mandate_options": None,
                        "network": None,
                        "request_three_d_secure": "automatic",
                    }
                },
                "payment_method_types": ["card"],
                "processing": None,
                "receipt_email": None,
                "review": None,
                "setup_future_usage": None,
                "shipping": None,
                "source": None,
                "statement_descriptor": None,
                "statement_descriptor_suffix": None,
                "status": "succeeded",
                "transfer_data": None,
                "transfer_group": None,
            }
        },
        "livemode": False,
        "pending_webhooks": 3,
        "request": {
            "id": "req_Q50llYH7NrdKeN",
            "idempotency_key": "359d36f4-80a2-4138-bd2d-0846239a6cc4",
        },
        "type": "payment_intent.succeeded",
    }


@pytest.fixture
def mock_stripe_webhook_construct_event_success(
    stripe_payment_intent_success_webhook_data: dict,
) -> Iterator:
    pather = patch(
        "stripe.Webhook.construct_event",
        return_value=stripe.util.convert_to_dict(
            stripe_payment_intent_success_webhook_data
        ),
    )
    yield pather.start()
    pather.stop()


@pytest.fixture
def mock_stripe_webhook_construct_event_failed() -> Iterator:
    patcher = patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("error", "sig_header"),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_create_refund_success() -> Iterator:
    patcher = patch("stripe.Refund.create", return_value=None)
    yield patcher.start()
    patcher.stop()


@pytest.fixture(scope="session")
def customer_order_path() -> str:
    return "/api/v1/customers-orders/"


@pytest.fixture
def mock_transition_to():
    patcher = patch(
        "core_app.models.OrderModel.transition_to",
        side_effect=Exception("Raised by unit test"),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def post_data_for_order_with_asap_delivery(
    address_id: int,
    customer_id: int,
    cooker_id: int,
) -> dict:
    return {
        "addressID": address_id,
        "customerID": customer_id,
        "cookerID": cooker_id,
        "items": json.dumps(
            [
                {"dishID": "11", "dishOrderedQuantity": 1},
                {"drinkID": "2", "drinkOrderedQuantity": 3},
            ]
        ),
    }
