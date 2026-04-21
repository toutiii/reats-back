import pytest
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient
from utils.enums import ErrorCodeEnum


@pytest.mark.django_db
class TestLogoutApi:
    @pytest.fixture
    def logout_path(self) -> str:
        return "/api/v1/logout/"

    @pytest.fixture
    def token_path(self) -> str:
        return "/api/v1/token/"

    @pytest.fixture
    def refresh_token_path(self) -> str:
        return "/api/v1/token/refresh/"

    @pytest.fixture
    def auth_data(self) -> dict:
        return {"phone": "0600000003"}

    def test_logout_and_refresh_token_blacklist(
        self,
        client: APIClient,
        logout_path: str,
        token_path: str,
        refresh_token_path: str,
        auth_data: dict,
        cooker_api_key_header: dict,
    ) -> None:
        with freeze_time("2024-01-07T14:00:00+00:00"):
            # 1. Ask for a token
            response = client.post(
                token_path,
                encode_multipart(BOUNDARY, auth_data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )
            assert response.status_code == status.HTTP_200_OK

            access_token = response.json()["data"]["token"]["access"]
            refresh_token = response.json()["data"]["token"]["refresh"]
            auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

            # 2. Try to verify refresh token works before logout
            refresh_response = client.post(
                refresh_token_path,
                encode_multipart(BOUNDARY, {"refresh": refresh_token}),
                content_type=MULTIPART_CONTENT,
                follow=False,
            )
            assert refresh_response.status_code == status.HTTP_200_OK

            # The setting ROTATE_REFRESH_TOKENS=True will give a NEW refresh token.
            new_refresh_token = refresh_response.json()["data"]["refresh"]

            # 3. Call logout endpoint
            logout_response = client.post(
                logout_path,
                encode_multipart(BOUNDARY, {"refresh": new_refresh_token}),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **auth_header,
            )
            assert logout_response.status_code == status.HTTP_200_OK

            # 4. Use the blacklisted refresh token to try to renew access token -> should fail
            failed_refresh_response = client.post(
                refresh_token_path,
                encode_multipart(BOUNDARY, {"refresh": new_refresh_token}),
                content_type=MULTIPART_CONTENT,
                follow=False,
            )

            assert failed_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
            assert failed_refresh_response.json().get("error", {}).get("code") == ErrorCodeEnum.TOKEN_NOT_VALID
