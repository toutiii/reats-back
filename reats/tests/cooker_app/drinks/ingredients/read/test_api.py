import pytest
from core_app.models import IngredientDrinkModel
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def ingredients_path(path: str) -> str:
    return f"{path}ingredients/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ingredients_to_create",
    [
        [
            {"code": "sucre", "name": "Sucre Blanc", "category": "sucre", "is_allergen": False},
            {"code": "lait", "name": "Lait entier", "category": "laitier", "is_allergen": True},
        ]
    ],
)
def test_list_drink_ingredients_returns_all(
    auth_headers: dict, client: APIClient, ingredients_path: str, ingredients_to_create: list[dict]
) -> None:
    for data in ingredients_to_create:
        IngredientDrinkModel.objects.create(**data)

    response = client.get(
        ingredients_path,
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    assert data is not None
    assert "ingredients" in data
    assert "categories" in data

    ingredients = data.get("ingredients")
    assert isinstance(ingredients, list)
    assert len(ingredients) >= len(ingredients_to_create)

    item = ingredients[0]
    for key in ["id", "code", "name", "category", "is_allergen"]:
        assert key in item

    categories = data.get("categories")
    assert isinstance(categories, list)
    assert len(categories) > 0
    assert "id" in categories[0]
    assert "name" in categories[0]
    assert "count" in categories[0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "search_term, expected_code",
    [
        ("miel", "miel"),
        ("cacahuete", "cacahuete"),
    ],
)
def test_search_drink_ingredients(
    auth_headers: dict, client: APIClient, ingredients_path: str, search_term: str, expected_code: str
) -> None:
    IngredientDrinkModel.objects.get_or_create(
        code="miel", defaults={"name": "Miel pur", "category": "sucre", "is_allergen": False}
    )
    IngredientDrinkModel.objects.get_or_create(
        code="cacahuete", defaults={"name": "Cacahuète", "category": "fruit_a_coque", "is_allergen": True}
    )

    response = client.get(
        f"{ingredients_path}?search={search_term}",
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    ingredients = data.get("ingredients")
    assert isinstance(ingredients, list)

    assert any(res["code"] == expected_code for res in ingredients)


@pytest.mark.django_db
def test_list_drink_ingredients_empty_db(auth_headers: dict, client: APIClient, ingredients_path: str) -> None:
    IngredientDrinkModel.objects.all().delete()

    response = client.get(
        ingredients_path,
        follow=False,
        **auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json().get("data")
    ingredients = data.get("ingredients")
    assert isinstance(ingredients, list)
    assert len(ingredients) == 0
