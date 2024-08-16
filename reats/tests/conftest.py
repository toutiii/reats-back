import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Iterator
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
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


@pytest.fixture(autouse=True)
def mock_googlemaps_distance_matrix() -> Iterator:
    patcher = patch(
        "utils.distance_computer.google_map_client.distance_matrix",
        return_value={
            "destination_addresses": [
                "1 Rue André Lalande, 91000 Évry-Courcouronnes, " "France",
                "49 Rue de la Clairière, 91000 Évry-Courcouronnes, " "France",
                "52 Av. de la Commune de Paris, 91220 " "Brétigny-sur-Orge, France",
                "14 Rue Marie Roche, 91090 Lisses, France",
            ],
            "origin_addresses": ["1 Rue René Cassin, 91100 Corbeil-Essonnes, France"],
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "9.2 km", "value": 9206},
                            "duration": {"text": "13 mins", "value": 800},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "12.0 km", "value": 11955},
                            "duration": {"text": "15 mins", "value": 886},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "22.0 km", "value": 21955},
                            "duration": {"text": "24 mins", "value": 1417},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "9.2 km", "value": 9160},
                            "duration": {"text": "13 mins", "value": 797},
                            "status": "OK",
                        },
                    ]
                }
            ],
        },
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
