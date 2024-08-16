import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_get_dishes_countries(
    auth_headers: dict,
    client: APIClient,
    customer_dishes_countries_path: str,
):
    response = client.get(
        f"{customer_dishes_countries_path}",
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "ok": True,
        "status_code": 200,
        "data": [
            "Benin",
            "Cameroun",
            "Congo",
            "Nigeria",
        ],
    }
