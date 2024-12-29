import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from core_app.models import DeliverModel
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def post_data_without_photo() -> dict:
    return {
        "delivery_radius": 5,
        "town": "New town",
        "delivery_vehicle": "car",
        "firstname": "New John test delivery",
        "lastname": "DOE AGAIN",
    }


@pytest.fixture
def post_data_with_photo(
    image: InMemoryUploadedFile,
    post_data_without_photo: dict,
) -> dict:
    return {
        **post_data_without_photo,
        "photo": image,
    }


@pytest.fixture
def deliver_id() -> int:
    return 1


@pytest.mark.django_db
class TestUpdateDeliverAccountInfoWithoutPhoto:
    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        deliver_id: int,
        path: str,
        post_data_without_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:

        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{deliver_id}/",
                encode_multipart(BOUNDARY, post_data_without_photo),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            deliver: DeliverModel = DeliverModel.objects.get(pk=deliver_id)

            assert deliver.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert deliver.photo == "delivers/1/profile_pics/default-profile-pic.jpg"
            assert deliver.delivery_radius == 5
            assert deliver.town == "New town"
            assert deliver.delivery_vehicle == "car"
            assert deliver.firstname == "New John test delivery"
            assert deliver.lastname == "DOE AGAIN"

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateDeliverAccountInfoWithPhotoV1:
    """
    Here the initial photo is the default one which is not supposed
    to be deleted by the update
    """

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        deliver_id: int,
        path: str,
        post_data_with_photo: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{deliver_id}/",
                encode_multipart(BOUNDARY, post_data_with_photo),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            deliver = DeliverModel.objects.get(pk=deliver_id)

            assert deliver.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert deliver.photo == "delivers/1/profile_pics/test.jpg"
            assert deliver.delivery_radius == 5
            assert deliver.town == "New town"
            assert deliver.delivery_vehicle == "car"
            assert deliver.firstname == "New John test delivery"
            assert deliver.lastname == "DOE AGAIN"

            upload_fileobj.assert_called_once()
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "delivers/1/profile_pics/test.jpg"
            delete_object.assert_not_called()


@pytest.mark.django_db
class TestUpdateDeliverAccountInfoWithPhotoV2:
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
    def post_data_with_photo_v2(
        self,
        second_profile_pic: InMemoryUploadedFile,
    ) -> dict:
        return {
            "firstname": "John",
            "lastname": "DOE",
            "photo": second_profile_pic,
        }

    def test_response(
        self,
        auth_headers: dict,
        client: APIClient,
        delete_object: MagicMock,
        deliver_id: int,
        path: str,
        post_data_with_photo: dict,
        post_data_with_photo_v2: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{deliver_id}/",
                encode_multipart(
                    BOUNDARY,
                    post_data_with_photo,
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            deliver = DeliverModel.objects.get(pk=deliver_id)

            assert deliver.modified.isoformat() == "2023-10-14T22:00:00+00:00"
            assert deliver.photo == "delivers/1/profile_pics/test.jpg"

            upload_fileobj.call_count == 1
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "test.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "delivers/1/profile_pics/test.jpg"
            delete_object.assert_not_called()

        # SECOND CALL #
        with freeze_time("2023-10-22T22:00:00+00:00"):
            response = client.patch(
                f"{path}{deliver_id}/",
                encode_multipart(
                    BOUNDARY,
                    post_data_with_photo_v2,
                ),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            deliver = DeliverModel.objects.get(pk=deliver_id)

            assert deliver.modified.isoformat() == "2023-10-22T22:00:00+00:00"
            assert deliver.photo == "delivers/1/profile_pics/second_profile_pic.jpg"

            upload_fileobj.call_count == 2
            assert len(upload_fileobj.call_args.args) == 3

            arg1, arg2, arg3 = upload_fileobj.call_args.args

            assert isinstance(arg1, InMemoryUploadedFile)
            assert arg1.name == "second_profile_pic.jpg"
            assert arg2 == "reats-dev-bucket"
            assert arg3 == "delivers/1/profile_pics/second_profile_pic.jpg"

            delete_object.assert_called_once_with(
                Bucket="reats-dev-bucket",
                Key="delivers/1/profile_pics/test.jpg",
            )


@pytest.mark.django_db
class TestUpdateDeliverFailedWithTokenSignedByAnUnknownPrivateKey:
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
        due_date = datetime.now(timezone.utc) + timedelta(minutes=60)
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
        deliver_id: int,
        path: str,
        data: dict,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{deliver_id}/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **wrong_auth_header,
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json().get("error_code") == "token_not_valid"


@pytest.mark.django_db
class TestRequestIsRejectedWithExpiredAccessToken:
    @pytest.fixture(scope="class")
    def expired_access_token(self) -> str:
        return """Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoi
YWNjZXNzIiwiZXhwIjoxNzA0NTY5MDk3LCJpYXQiOjE3MDQ1Njg3OTcsImp0aSI6IjB
iZDM5OTI1MDU5NTQxYmM4MGNiNTk0ZTQ3YjU3MmY1IiwidXNlcl9pZCI6NH0.P2JPrF
j0czpJeNzYtd7l7beMZuooP2vsyED3PqogYewJBSycurei1EVOGBF-hSzSryxpL4q3H
ZD9hWTanL_44j19IqDE0aZWPRsjMQAVHyJsg36KQvjmkXUYPyliMIxY11GcEzzb3s8e
vs3f7F2KXip8w5RaVaQuWOGDof137D4jDei-PIAHdnC4f64NIiMazNX2-BzCHMoAKVa
dLog8S0GtmuY3tPGOgHoqu5L5mXR6Ea8BH_x0lcXW5pFFpR6Mk1pdKhi6ZKuc0VnGU2
vWVKl8aFYiCLU1Lx2vTpkG0fqziSqcxCofG_Y-cEMoDpLW51ESoItVEGJE5me7YQXNU
ggC3pc9izQZENtdW8Z6L7KkWPf-h4S6wfEMI1dVK1Y-Jcg7MXwgyAgRCnnSBjaO89rq
JTJFR2KO9elgH9RtMDCSTXocepnoop-SDri1qN8AKyNoIrYQFmMm5FhQam636jwkTYI
8yZ6DgakrNf2nzPoHBXtF6yHyCe_EUwRMnJ4gMmseQi4hPNNqZh3aMdvyEjOBNpaCgJ
N1t6w1knQaNpkJtxf4kzLSq0zdATk7GHF2NqP6cIi3zmbJyG-jqG3Y-LGZlpWWBk_ZZ
ct4oFdWCTtEg1i4CV0LS43lOnu1Gv168nOvqc-WFXqMMNJnT88Ruz1St96KbpPw0m6K
7tWuyyI"""

    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {}

    def test_response(
        self,
        expired_access_token: str,
        client: APIClient,
        deliver_id: int,
        path: str,
        data: dict,
    ) -> None:
        expired_auth_header = {
            "HTTP_AUTHORIZATION": expired_access_token.replace("\n", "")
        }
        response = client.patch(
            f"{path}{deliver_id}/",
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **expired_auth_header,
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json().get("error_code") == "token_not_valid"
