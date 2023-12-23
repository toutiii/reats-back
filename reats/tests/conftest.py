from io import BytesIO
from typing import Iterator
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
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
