import pytest
from core_app.models import CookerModel, DishModel
from core_app.serializers import DishDetailSerializer


@pytest.mark.django_db
class TestDishMarginCalculation:
    def test_margin_property_with_cost(self):
        """Test du calcul de la marge avec cost défini."""
        cooker = CookerModel.objects.get(pk=1)
        dish = DishModel.objects.create(
            name="Test Dish",
            price=20.0,
            cost=8.0,
            cooker=cooker,
            category="dish",
            country="France",
        )
        assert dish.margin == 60.0  # ((20 - 8) / 20) * 100

    def test_margin_property_without_cost(self):
        """Test du calcul de la marge sans cost."""
        cooker = CookerModel.objects.get(pk=1)
        dish = DishModel.objects.create(
            name="Test Dish",
            price=20.0,
            cost=None,
            cooker=cooker,
            category="dish",
            country="France",
        )
        assert dish.margin is None

    def test_margin_property_with_zero_price(self):
        """Test du calcul de la marge avec prix à zéro."""
        cooker = CookerModel.objects.get(pk=1)
        dish = DishModel.objects.create(
            name="Test Dish",
            price=0.0,
            cost=5.0,
            cooker=cooker,
            category="dish",
            country="France",
        )
        assert dish.margin is None

    def test_margin_in_serializer(self):
        """Vérifie que le serializer expose la marge."""
        cooker = CookerModel.objects.get(pk=1)
        dish = DishModel.objects.create(
            name="Test",
            price=15.0,
            cost=5.0,
            preparation_time=10,
            max_concurrent_orders=5,
            cooker=cooker,
            category="dish",
            country="France",
        )
        serializer = DishDetailSerializer(dish)
        data = serializer.data

        assert "margin" in data
        assert data["margin"] == 66.67
        assert data["cost"] == 5.0
        assert data["preparation_time"] == 10
        assert data["max_concurrent_orders"] == 5
