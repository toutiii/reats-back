import pytest


@pytest.fixture
def path() -> str:
    return "/api/v1/dishes/"


@pytest.fixture
def post_data_with_financial_fields(image) -> dict:
    """Fixture pour les données POST avec les champs financiers."""
    return {
        "category": "dish",
        "cooker": 1,
        "country": "France",
        "description": "Plat test avec données financières",
        "name": "Burger Premium",
        "photo": image,
        "price": "20.0",
        "cost": "8.0",
        "preparation_time": 15,
        "max_concurrent_orders": 10,
    }
