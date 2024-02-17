import pytest
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_empty_query_params(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("data") is None
    assert response.json() == {"ok": True, "status_code": status.HTTP_404_NOT_FOUND}


@pytest.mark.django_db
def test_get_enabled_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"is_enabled": "true"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_disabled_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"is_enabled": "false"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("is_enabled") is False


@pytest.mark.django_db
def test_get_starters(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "starter"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "starter"


@pytest.mark.django_db
def test_get_dishes(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "dish"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dish"


@pytest.mark.django_db
def test_get_desserts(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "dessert"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") == "dessert"


@pytest.mark.django_db
def test_get_all_categories(auth_headers: dict, client: APIClient, path: str) -> None:
    response = client.get(
        path,
        {"category": "starter,dish,dessert"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") in (True, False)


@pytest.mark.django_db
def test_get_all_enabled_categories(
    auth_headers: dict, client: APIClient, path: str
) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "true",
        },
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is True


@pytest.mark.django_db
def test_get_all_disabled_categories(
    auth_headers: dict, client: APIClient, path: str
) -> None:
    response = client.get(
        path,
        {
            "category": "starter,dish,dessert",
            "is_enabled": "false",
        },
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("ok") is True
    assert response.json().get("status_code") == status.HTTP_200_OK
    assert response.json().get("data") is not None

    for item in response.json().get("data"):
        assert item.get("category") in ("starter", "dish", "dessert")
        assert item.get("is_enabled") is False


@pytest.mark.django_db
class TestOneCookerCantSeeOtherCookerDishes:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33600000003"}

    def test_response(
        self,
        cooker_api_key_header: dict,
        client: APIClient,
        data: dict,
        path: str,
        token_path: str,
    ) -> None:
        with freeze_time("2024-01-20T17:05:45+00:00"):
            # First we ask a token as usual
            token_response = client.post(
                token_path,
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **cooker_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

            # Then we can ask for some dishes
            response = client.get(
                path,
                {"name": "Pou"},
                follow=False,
                **access_auth_header,
            )
            assert response.status_code == status.HTTP_200_OK

            assert response.json().get("data") is None
