import os
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from cooker_app.models import CookerModel
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def post_address_data() -> dict:
    return {
        "postal_code": "89000",
        "street_name": "rue René Cassin",
        "street_number": "99",
        "town": "EVREUX",
        "address_complement": "résidence de la brume",
    }


@pytest.fixture
def post_personal_information_data_without_photo() -> dict:
    return {
        "firstname": "John",
        "lastname": "DOE",
        "max_order_number": 12,
    }


@pytest.fixture
def post_personal_information_data_with_photo(image: InMemoryUploadedFile) -> dict:
    return {
        "firstname": "John",
        "lastname": "DOE",
        "max_order_number": 12,
        "photo": image,
    }


@pytest.fixture
def cooker_id() -> int:
    return 1


@pytest.mark.django_db
class TestUpdateCookerAddressInfo:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        cooker_id: int,
        path: str,
        post_address_data: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, post_address_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert cooker.postal_code == "89000"
            assert cooker.street_name == "rue René Cassin"
            assert cooker.street_number == "99"
            assert cooker.town == "EVREUX"
            assert cooker.address_complement == "résidence de la brume"

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateCookerAccountInfoWithoutPhoto:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        cooker_id: int,
        path: str,
        post_personal_information_data_without_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(
                    BOUNDARY, post_personal_information_data_without_photo
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert cooker.firstname == "John"
            assert cooker.lastname == "DOE"
            assert cooker.max_order_number == 12

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateCookerAccountInfoWithPhotoV1:
    """
    Here the initial photo is the default one which is not supposed
    to be deleted by the update
    """

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        cooker_id: int,
        path: str,
        post_personal_information_data_with_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, post_personal_information_data_with_photo),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert cooker.firstname == "John"
            assert cooker.lastname == "DOE"
            assert cooker.max_order_number == 12
            assert cooker.photo == "cookers/1/profile_pics/test.jpg"

            upload_fileobj.assert_called_once()
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "cookers/1/profile_pics/test.jpg"
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateCookerAccountInfoWithPhotoV2:
    """
    Here the initial photo is not the default one so we expect a deletion in S3 here.
    """

    @pytest.fixture
    def second_profile_pic(self) -> InMemoryUploadedFile:
        im = Image.new(mode="RGB", size=(200, 200))  # create a new image using PIL
        im_io = BytesIO()  # a BytesIO object for saving image
        im.save(im_io, "JPEG")  # save the image to im_io
        im_io.seek(0)  # seek to the beginning

        image = InMemoryUploadedFile(
            im_io,
            None,
            "second_profile_pic.jpg",
            "image/jpeg",
            len(im_io.getvalue()),
            None,
        )

        return image

    @pytest.fixture
    def second_post_personal_information_data_with_photo(
        self,
        second_profile_pic: InMemoryUploadedFile,
    ) -> dict:
        return {
            "firstname": "John",
            "lastname": "DOE",
            "max_order_number": 12,
            "photo": second_profile_pic,
        }

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        cooker_id: int,
        path: str,
        post_personal_information_data_with_photo: dict,
        second_post_personal_information_data_with_photo: dict,
        upload_fileobj: MagicMock,
        second_profile_pic: InMemoryUploadedFile,
        image: InMemoryUploadedFile,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(
                    BOUNDARY,
                    post_personal_information_data_with_photo,
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert cooker.firstname == "John"
            assert cooker.lastname == "DOE"
            assert cooker.max_order_number == 12
            assert cooker.photo == "cookers/1/profile_pics/test.jpg"

            upload_fileobj.call_count == 1
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "cookers/1/profile_pics/test.jpg"
            delete_object.assert_not_called()

        # SECOND CALL #
        with freeze_time("2023-10-22T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(
                    BOUNDARY,
                    second_post_personal_information_data_with_photo,
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-22T22:00:00+00:00"
            assert cooker.firstname == "John"
            assert cooker.lastname == "DOE"
            assert cooker.max_order_number == 12
            assert cooker.photo == "cookers/1/profile_pics/second_profile_pic.jpg"

            upload_fileobj.call_count == 2
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "second_profile_pic.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "cookers/1/profile_pics/second_profile_pic.jpg"

            delete_object.assert_called_once_with(
                Bucket="reats-dev-bucket",
                Key="cookers/1/profile_pics/test.jpg",
            )


@pytest.mark.django_db
class TestUpdateCookerOnlineStatus:
    @pytest.fixture
    def post_switch_cooker_online(self) -> dict:
        return {
            "is_online": True,
        }

    @pytest.fixture
    def post_switch_cooker_offline(self) -> dict:
        return {
            "is_online": False,
        }

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        cooker_id: int,
        path: str,
        post_switch_cooker_offline: dict,
        post_switch_cooker_online: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        cooker: CookerModel = CookerModel.objects.get(pk=cooker_id)
        assert cooker.is_online is False

        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert cooker.is_online is True

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()

        with freeze_time("2023-10-14T23:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_offline),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T23:00:00+00:00"
            assert cooker.is_online is False

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateCookerFailedWithTokenSignedByAnUnknownPrivateKey:
    @pytest.fixture(scope="class")
    def unknown_private_key(self) -> str:
        return """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEApkmnh3+BjZ3TjZWjZwgIxOz9hBKmmZoxLHDwkUI6k8pq7u7+
NZH2jWI7HPNDhCwX6UrZ5XOkGcsC3b1P2euwYk1KumvUqgdldqq4Yy2XbEG7hXcb
vKfyDygrU5yyWVXJjsiDm2wFI7i8BjN+2qXLgA85MgjNyVg5MFtlVc0upBLmteQO
T+th0pH92WjYxMA61pjkjmdzz3nHavm9soPHKm+DXD59D0bGaQTW3UHtMOTbTtWg
gPD+ZGRzXtGfprsb/0nQRBUi+SRs1m60AoESv9eU34/c0Wvjd1X51xr5fqKvD0Gc
V3KYhzsIuh9sIPwJxkaSKx5iOd32BsH9mzatMQIDAQABAoIBACY+sHJAiCprDzn0
HZXXyjSIkTIsG/cd+ItRGnM+OTy+hGOZwgvOG1efLRtWc8PVZFZ6qazVMPvhrjIT
lWb4hyPExRglLs9ATjzBvRDKbpYudBOZNl7ofYqw4W4kjvxu96GISoSXjoMNvOjs
NRPSqAA3AB+a2MGjMdwGWUMnor+HXkjT5V6KEJCe7r8XG4XKf7a8BkwxW8PNr4/r
EEL8fIwpR6Kh6obHTOXn6fIQgCV+GTfKxG6IX7oIT8XtC9rooMxF16QQojmnn5QX
b8BHimj7C8HtjuzUtnoGq/TNvCyVjnS3Bk+UB4roRn2pxgjw0NtY2Obm76FGJ4uE
wqxtLPECgYEA2r3reus0POLTdOmKw2fM5Dq6Am/WT3JKOYqoVUhtPAzoSazSy8T+
GTr/F0kt/8p4tcy53TCDiI1x2qSevzkl5htntRy//oakAGrsW8WwSB5duLN2niFz
q4bkxlcjcjZv7Wg+S3KACLkzNbOLK+JI6C0xCrOthIKOApBxnhWi7cUCgYEAwpyC
UA+4VNY1d7tWpH0z64D0lprT7ISQZA0lKVW+2I0qxJCi40vZb8vKRdq5R7RF4u7K
FUHGD73pnYefmFTp8t95Ntsr7yndFZXmp6jc6AnIuKRkGI05+bJ/vWKOS79libgs
9dmLova+jGyY+kaQ3GcA1qIf3DwhhRJXQ+/DhH0CgYBQ7O6PnTDITcqZeEWEIYTl
8uwaNrH81nWrcCby1kbDbqsJhsy94nV3dCInxUUlWwzphYJF2Mrw3BOBJmIssMHa
rczibm6BheJq3SPwl+St6b4WtR5vRkT68n70+gv9FzK1jFlvpD7F+258sZ4NcDw0
2XNJWEwbuAk93Z6LM8oBWQKBgDqZkgu1kBXLorH48S/6m2WwoPWwjVvM1wWph6UY
sqzWZShnPQUgU8r8HF5IbD4RJHIe4S7hbVhUIUJUElR2TTPa4s8H1ATiIDZduuSF
Tm94cr5WkeVqsShk/V3zjVF1wodjs/YbmZZqohn6oV3LXddgFLqMeveAC7/cM/a6
/a6pAoGAF0Vx8B97A2C+cGfE3RvHfPqPMWQ+ggE+MxIcJ0pKxzLxa6c8odmU3Jla
FhxtAirMySNzId/rIu6k6wPIqyziXjh0DBu0eI4flX3CJe1In0UfX9oqcFuw+VbY
2BsLflFNz7H1Cfq+x9ZLLg1JfluZOL7yIyvUb08IgUBsPfwMmM0=
-----END RSA PRIVATE KEY-----"""

    @pytest.fixture(scope="class")
    def token_signed_with_unknown_private_key(self, unknown_private_key: str) -> str:
        due_date = datetime.utcnow() + timedelta(minutes=60)
        payload = {
            "exp": int(due_date.timestamp()),
            "jti": str(uuid4()),
            "user_id": 1,
            "token_type": "access",
        }
        secret = load_pem_private_key(unknown_private_key.encode(), None)
        assert isinstance(secret, rsa.RSAPrivateKey)

        wrong_token = jwt.encode(
            payload,
            secret,
            algorithm=os.getenv("DJANGO_SIMPLE_JWT_ALGORITHM"),
        )

        return f"Bearer {wrong_token}"

    @pytest.fixture(scope="class")
    def wrong_auth_header(self, token_signed_with_unknown_private_key: str) -> dict:
        return {"HTTP_AUTHORIZATION": token_signed_with_unknown_private_key}

    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {}

    def test_response(
        self,
        wrong_auth_header: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        data: dict,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **wrong_auth_header,
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUpdateCookerFailedWithUnexpectedUserIDInToken:
    @pytest.fixture(scope="class")
    def token_with_unexpected_user_id(self, private_key: str) -> str:
        due_date = datetime.utcnow() + timedelta(minutes=60)
        payload = {
            "exp": int(due_date.timestamp()),
            "jti": str(uuid4()),
            "user_id": 100,  # Different user than cooker_id fixture
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

    @pytest.fixture(scope="class")
    def wrong_auth_header(self, token_with_unexpected_user_id: str) -> dict:
        return {"HTTP_AUTHORIZATION": token_with_unexpected_user_id}

    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {}

    def test_response(
        self,
        wrong_auth_header: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        data: dict,
    ) -> None:
        with freeze_time("2024-01-06T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **wrong_auth_header,
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
