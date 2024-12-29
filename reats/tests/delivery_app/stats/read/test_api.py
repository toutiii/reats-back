import pytest
from core_app.models import OrderModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def deliver_id() -> int:
    return 1


@pytest.mark.django_db
def test_delivery_orders_stats_with_right_dates(
    auth_headers: dict,
    client: APIClient,
    deliver_id: int,
    delivery_stats_path: str,
) -> None:

    # we check that the delivery man has some orders
    assert OrderModel.objects.filter(delivery_man__id=deliver_id).count() > 0

    response = client.get(
        delivery_stats_path,
        {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": {
            "delivery_mean_time": 720.0,
            "total_delivery_distance": 9.0,
            "total_delivery_fees": 9.7,
            "total_number_of_deliveries": 2,
        },
        "ok": True,
        "status_code": 200,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query_params",
    [
        {},
        {"start_date": "2024-01-01"},
        {"start_date": "invalid_date", "end_date": "2024-12-31"},
        {"start_date": "2024-01-01", "end_date": "invalid_date"},
        {"start_date": "invalid_date", "end_date": "invalid_date"},
        {"end_date": "2024-12-31"},
        {"start_date": "2024-12-31", "end_date": "2024-01-01"},
    ],
    ids=[
        "no dates provided",
        "only start date is provided",
        "both dates are provided but start date is invalid",
        "both dates are provided but end date is invalid",
        "both dates are invalid",
        "only end date provided",
        "start date is greater than end date",
    ],
)
def test_delivery_orders_stats_with_wrong_dates(
    auth_headers: dict,
    client: APIClient,
    deliver_id: int,
    delivery_stats_path: str,
    query_params: dict,
) -> None:

    # we check that the delivery man has some orders
    assert OrderModel.objects.filter(delivery_man__id=deliver_id).count() > 0

    response = client.get(
        delivery_stats_path,
        query_params,
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [],
        "ok": False,
        "status_code": 404,
    }


@pytest.mark.django_db
class TestDeliveryOrdersStatsFailedWithExpiredToken:
    @pytest.fixture(scope="class")
    def data(self) -> dict:
        return {"phone": "+33700000001"}

    def test_response(
        self,
        delivery_api_key_header: dict,
        client: APIClient,
        data: dict,
        delivery_stats_path: str,
    ) -> None:

        with freeze_time("2024-01-20T17:05:45+00:00"):
            token_response = client.post(
                "/api/v1/token/",
                encode_multipart(BOUNDARY, data),
                content_type=MULTIPART_CONTENT,
                follow=False,
                **delivery_api_key_header,
            )

            assert token_response.status_code == status.HTTP_200_OK
            access_token = token_response.json().get("token").get("access")
            access_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

        with freeze_time("2024-01-20T17:15:45+00:00"):
            response = client.get(
                f"{delivery_stats_path}",
                {"start_date": "2024-01-01", "end_date": "2024-12-31"},
                follow=False,
                **access_auth_header,
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json().get("error_code") == "token_not_valid"
