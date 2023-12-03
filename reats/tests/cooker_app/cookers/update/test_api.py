from io import BytesIO
from typing import Iterator
from unittest.mock import MagicMock, call, patch

import pytest
from cooker_app.models import CookerModel
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
            )

            assert response.status_code == status.HTTP_200_OK

            cooker = CookerModel.objects.get(pk=cooker_id)

            assert cooker.modified.isoformat() == "2023-10-14T23:00:00+00:00"
            assert cooker.is_online is False

            upload_fileobj.assert_not_called()
            delete_object.assert_not_called()
