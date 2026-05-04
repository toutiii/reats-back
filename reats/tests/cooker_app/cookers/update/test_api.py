import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from core_app.models import CookerModel
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum


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


@pytest.fixture
def cooker_response_keys() -> list:
    """Liste des clés essentielles à vérifier dans la réponse du profil Cooker."""
    return [
        "id",
        "firstname",
        "lastname",
        "email",
        "postal_code",
        "siret",
        "street_name",
        "street_number",
        "town",
        "address_complement",
        "max_order_number",
        "is_online",
    ]


def assert_response_structure(response_body: dict, expected_data: dict, keys: list) -> None:
    """Extrait un sous-ensemble de clés de la réponse et le compare aux données attendues."""
    actual_subset = {k: response_body["data"].get(k) for k in keys}
    assert actual_subset == expected_data


@pytest.mark.django_db
class TestUpdateCookerInfoSuccess:
    def test_update_personal_info(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        post_personal_information_data_without_photo: dict,
        cooker_response_keys: list,
    ) -> None:
        with freeze_time("2023-10-14T22:00:00+00:00"):
            response = client.patch(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, post_personal_information_data_without_photo),
                content_type=MULTIPART_CONTENT,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            response_body = response.json()
            assert response_body["success"] is True
            assert response_body["message"] == "Operation successful"

            assert_response_structure(
                response_body,
                {
                    "id": cooker_id,
                    "firstname": "John",
                    "lastname": "DOE",
                    "email": "test@gmail.com",
                    "postal_code": "91000",
                    "siret": "00000000000001",
                    "street_name": "rue André Lalande",
                    "street_number": "1",
                    "town": "Evry",
                    "address_complement": None,
                    "max_order_number": 12,
                    "is_online": True,
                },
                cooker_response_keys,
            )

            # On vérifie uniquement la date de modification en DB car elle n'est pas dans la réponse API
            cooker = CookerModel.objects.get(pk=cooker_id)
            assert cooker.modified.isoformat() == "2023-10-14T22:00:00+00:00"

    def test_update_personal_info_with_put(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        cooker_response_keys: list,
    ) -> None:
        # Fetch existing to populate mandatory fields for PUT
        existing = client.get(f"{path}{cooker_id}/", **auth_headers).json()["data"]

        full_put_data = {
            "firstname": "Jane",
            "lastname": "DOEE",
            "email": "jane.doee@test.com",
            "postal_code": existing["address_section"]["postal_code"],
            "siret": existing["personal_infos_section"]["siret"],
            "street_name": "New Street",
            "street_number": "100",
            "town": "NEW TOWN",
            "max_order_number": 15,
            "is_online": True,
        }

        with freeze_time("2023-10-15T22:00:00+00:00"):
            response = client.put(
                f"{path}{cooker_id}/",
                encode_multipart(BOUNDARY, full_put_data),
                content_type=MULTIPART_CONTENT,
                **auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            response_body = response.json()
            assert response_body["success"] is True
            assert response_body["message"] == "Operation successful"

            assert_response_structure(
                response_body,
                {
                    "id": cooker_id,
                    "firstname": "Jane",
                    "lastname": "DOEE",
                    "email": "jane.doee@test.com",
                    "postal_code": existing["address_section"]["postal_code"],
                    "siret": existing["personal_infos_section"]["siret"],
                    "street_name": "New Street",
                    "street_number": "100",
                    "town": "NEW TOWN",
                    "address_complement": None,
                    "max_order_number": 15,
                    "is_online": True,
                },
                cooker_response_keys,
            )

            # On vérifie uniquement la date de modification en DB car elle n'est pas dans la réponse API
            cooker = CookerModel.objects.get(pk=cooker_id)
            assert cooker.modified.isoformat() == "2023-10-15T22:00:00+00:00"

    def test_update_address(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        post_address_data: dict,
    ) -> None:
        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, post_address_data),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        cooker = CookerModel.objects.get(pk=cooker_id)
        assert cooker.postal_code == "89000"
        assert cooker.street_name == "rue René Cassin"


@pytest.mark.django_db
class TestUpdateCookerInfoFailure:
    def test_update_info_invalid_id(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        """PATCH on a non-existent cooker ID → 404 Not Found."""
        response = client.patch(
            f"{path}9999/",
            encode_multipart(BOUNDARY, {"firstname": "Ghost"}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_info_uniqueness_conflict(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
    ) -> None:
        """PATCH that creates a unique constraint violation → 400 Bad Request."""
        CookerModel.objects.create(
            phone="0711111111", email="other@test.com", siret="12345678901235", lastname="Other", firstname="User"
        )

        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, {"email": "other@test.com"}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
class TestUpdateCookerStrictContract:
    """
    Validates the strict PATCH contract on the cooker profile endpoint.

    CTO requirements:
      1. PATCH with only authorized fields → 200 OK, data correctly updated.
      2. PATCH containing at least one forbidden field (e.g. phone) → 400 Bad Request.
      3. PATCH with valid fields but targeting a different cooker → 403 Forbidden.
    """

    def test_patch_with_allowed_fields_succeeds(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        cooker_response_keys: list,
    ) -> None:
        """Test 1: PATCH with only authorized fields → 200 OK."""
        payload = {
            "firstname": "Jean",
            "lastname": "MARTIN",
            "max_order_number": 5,
        }
        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, payload),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_body = response.json()
        assert response_body["success"] is True

        assert_response_structure(
            response_body,
            {
                "id": cooker_id,
                "firstname": "Jean",
                "lastname": "MARTIN",
                "email": "test@gmail.com",
                "postal_code": "91000",
                "siret": "00000000000001",
                "street_name": "rue André Lalande",
                "street_number": "1",
                "town": "Evry",
                "address_complement": None,
                "max_order_number": 5,
                "is_online": True,
            },
            cooker_response_keys,
        )

        cooker = CookerModel.objects.get(pk=cooker_id)
        assert cooker.firstname == "Jean"
        assert cooker.lastname == "MARTIN"
        assert cooker.max_order_number == 5

    def test_patch_with_forbidden_field_returns_400(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
    ) -> None:
        """Test 2: PATCH containing a forbidden field (phone) → 400 Bad Request."""
        payload = {
            "firstname": "Jean",
            "phone": "0600000099",  # phone has its own endpoint with OTP verification
        }
        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, payload),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_sensitive_fields_return_400(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
    ) -> None:
        """Test 2b: PATCH containing sensitive admin fields → 400 Bad Request."""
        payload = {
            "firstname": "Jean",
            "acceptance_rate": 10,  # read-only field managed internally
            "is_activated": False,  # read-only field managed internally
        }
        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, payload),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_another_cooker_returns_403(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
    ) -> None:
        """Test 3: PATCH with valid fields but targeting another cooker's ID → 403 Forbidden."""
        other_cooker = CookerModel.objects.create(
            phone="0722222222",
            email="other3@reats.com",
            siret="12345678901237",
            lastname="Autre",
            firstname="Cuisinier",
        )
        payload = {"firstname": "Hacker"}
        response = client.patch(
            f"{path}{other_cooker.pk}/",
            encode_multipart(BOUNDARY, payload),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUpdateCookerPhotoSuccess:
    def test_upload_initial_photo(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        image: InMemoryUploadedFile,
        upload_fileobj: MagicMock,
        delete_object: MagicMock,
    ) -> None:
        response = client.patch(
            f"{path}{cooker_id}/photo/",
            encode_multipart(BOUNDARY, {"photo": image}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        cooker = CookerModel.objects.get(pk=cooker_id)
        assert "profile_pics/test.jpg" in cooker.photo
        upload_fileobj.assert_called_once()
        delete_object.assert_not_called()  # Default photo should not be deleted

    def test_replace_existing_photo(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
        image: InMemoryUploadedFile,
        upload_fileobj: MagicMock,
        delete_object: MagicMock,
    ) -> None:
        # Setup: first photo already exists (non-default)
        cooker = CookerModel.objects.get(pk=cooker_id)
        cooker.photo = "cookers/1/profile_pics/old.jpg"
        cooker.save()

        response = client.patch(
            f"{path}{cooker_id}/photo/",
            encode_multipart(BOUNDARY, {"photo": image}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        delete_object.assert_called_once()
        assert delete_object.call_args.kwargs["Key"] == "cookers/1/profile_pics/old.jpg"


@pytest.mark.django_db
class TestUpdateCookerPhotoFailure:
    def test_upload_no_photo(
        self,
        auth_headers: dict,
        client: APIClient,
        cooker_id: int,
        path: str,
    ) -> None:
        response = client.patch(
            f"{path}{cooker_id}/photo/",
            encode_multipart(BOUNDARY, {}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_DATA"

    def test_upload_invalid_id(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        image: InMemoryUploadedFile,
    ) -> None:
        response = client.patch(
            f"{path}9999/photo/",
            encode_multipart(BOUNDARY, {"photo": image}),
            content_type=MULTIPART_CONTENT,
            **auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


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
        assert cooker.is_online is True

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
        assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID


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
        cooker_id: int,
        path: str,
        data: dict,
    ) -> None:
        expired_auth_header = {"HTTP_AUTHORIZATION": expired_access_token.replace("\n", "")}
        response = client.patch(
            f"{path}{cooker_id}/",
            encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **expired_auth_header,
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID


@pytest.mark.django_db
class TestAccessTokenRenew:
    @pytest.fixture
    def post_switch_cooker_online(self) -> dict:
        return {
            "is_online": True,
        }

    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "0600000003"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        cooker_id: int,
        data: dict,
        path: str,
        post_switch_cooker_online: dict,
        refresh_token_path: str,
        token_path: str,
    ) -> None:
        with freeze_time("2024-01-07T14:00:00+00:00") as frozen_datetime:
            # First we ask a token as usual
            response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json().get("success") is True
            assert response.json().get("data").get("token") is not None
            assert response.json().get("data").get("user_id") is not None

            # Extracting access and refresh tokens from the API response
            access_token = response.json().get("data").get("token").get("access")
            refresh_token = response.json().get("data").get("token").get("refresh")
            user_id = response.json().get("data").get("user_id")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
            refresh_token_data = {"refresh": refresh_token}

            # Secondly we try a simple request:
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_200_OK

            # Going to 5 min in the future
            token_expired_date = datetime.now(timezone.utc) + timedelta(minutes=5)
            frozen_datetime.move_to(token_expired_date)

            # Then we attempt the same request as 5 min ago
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID
            assert response.json().get("success") is False

            # We try now to ask a new access token using the refresh token
            response = client.post(
                refresh_token_path,
                encode_multipart(BOUNDARY, refresh_token_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json().get("success") is True
            assert response.json().get("data").get("access") is not None

            new_access_token = response.json().get("data").get("access")
            assert new_access_token != access_token

            # Finally we try again the request with our new access token
            new_access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {new_access_token}"}
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **new_access_auth_header,
            )
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRefreshTokenRenew:
    @pytest.fixture
    def post_switch_cooker_online(self) -> dict:
        return {
            "is_online": True,
        }

    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "0600000003"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        cooker_id: int,
        data: dict,
        path: str,
        post_switch_cooker_online: dict,
        refresh_token_path: str,
        token_path: str,
    ) -> None:
        with freeze_time("2024-01-13T14:00:00+00:00") as frozen_datetime:
            # First we ask a token pair as usual
            response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json().get("success") is True
            assert response.json().get("data").get("token") is not None
            assert response.json().get("data").get("user_id") is not None

            # Extracting access and refresh tokens from the API response
            access_token = response.json().get("data").get("token").get("access")
            refresh_token = response.json().get("data").get("token").get("refresh")
            user_id = response.json().get("data").get("user_id")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
            refresh_token_data = {"refresh": refresh_token}

            # Secondly we try a simple request:
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_200_OK

            # Travel to one day and plus in the future
            refresh_token_expired_date = datetime.now(timezone.utc) + timedelta(hours=24.1)
            frozen_datetime.move_to(refresh_token_expired_date)

            # Then we attempt the same request as approximtively 24h ago
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID

            # We try now to ask a new access token using the expired refresh token
            response = client.post(
                refresh_token_path,
                encode_multipart(BOUNDARY, refresh_token_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error").get("code") == ErrorCodeEnum.TOKEN_NOT_VALID

            # So now we have to ask again a new token pair
            response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json().get("success") is True
            assert response.json().get("data").get("token") is not None
            assert response.json().get("data").get("user_id") is not None

            # Finally we try again the request with our new access token
            new_access_token = response.json().get("data").get("token").get("access")
            new_access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {new_access_token}"}
            response = client.patch(
                f"{path}{user_id}/",
                encode_multipart(BOUNDARY, post_switch_cooker_online),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **new_access_auth_header,
            )
            assert response.status_code == status.HTTP_200_OK
