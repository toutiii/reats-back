from unittest.mock import MagicMock

import pytest
from core_app.models import DishModel
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCreateDishWithFinancialFields:
    def test_create_dish_with_cost_and_preparation_time(
        self,
        auth_headers: dict,
        client: APIClient,
        path: str,
        post_data_with_financial_fields: dict,
        upload_fileobj: MagicMock,
    ) -> None:
        """Test de création d'un plat avec les champs financiers."""
        response = client.post(
            path,
            encode_multipart(BOUNDARY, post_data_with_financial_fields),
            content_type=MULTIPART_CONTENT,
            follow=False,
            **auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        dish = DishModel.objects.latest("pk")
        assert dish.cost == 8.0
        assert dish.preparation_time == 15
        assert dish.max_concurrent_orders == 10
