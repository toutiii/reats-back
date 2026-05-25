import random
from datetime import timedelta
from typing import cast

from core_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    DeliverModel,
    DishImageModel,
    DishModel,
    DishNutritionalInfo,
    DrinkImageModel,
    DrinkModel,
    DrinkNutritionalInfo,
    IngredientDrinkModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from utils.enums import OrderStatusEnum

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with initial data for development (Users, Menu, Orders)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            type=str,
            required=True,
            help="Phone number used to create/retrieve sample customer, cooker, and deliver users.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting data seeding..."))
        phone = options["phone"].strip()

        # --- 0. Superuser Creation ---
        superuser_email = "admin@reats.com"
        if not User.objects.filter(username=superuser_email).exists():
            User.objects.create_superuser(  # ty: ignore[unresolved-attribute]
                username=superuser_email,
                email=superuser_email,
                password="password",
            )
            self.stdout.write(f"Created Superuser: {superuser_email}")
        else:
            self.stdout.write(f"Superuser already exists: {superuser_email}")

        # --- 1. Users Creation ---

        # Cooker
        cooker, created = CookerModel.objects.get_or_create(
            email="cooker@example.com",
            defaults={
                "firstname": "John",
                "lastname": "Doe",
                "phone": phone,
                "siret": "12345678901234",
                "postal_code": "75001",
                "town": "Paris",
                "street_name": "Rue de Rivoli",
                "street_number": "1",
                "is_activated": True,
                "is_online": True,
            },
        )
        if created:
            self.stdout.write(f"Created Cooker: {cooker.email}")
        else:
            self.stdout.write(f"Cooker already exists: {cooker.email}")

        # Customer
        customer, created = CustomerModel.objects.get_or_create(
            phone=phone,
            defaults={
                "firstname": "Jane",
                "lastname": "Smith",
                "is_activated": True,
            },
        )
        if created:
            self.stdout.write(f"Created Customer: {customer.phone}")
            AddressModel.objects.create(
                customer=customer,
                street_name="Avenue des Champs-Élysées",
                street_number="10",
                town="Paris",
                postal_code="75008",
            )
        else:
            self.stdout.write(f"Customer already exists: {customer.phone}")

        # Deliver
        deliver, created = DeliverModel.objects.get_or_create(
            phone=phone,
            defaults={
                "firstname": "Jack",
                "lastname": "Fast",
                "delivery_vehicle": "bike",
                "town": "Paris",
                "delivery_radius": 5,
                "siret": "98765432109876",
                "is_activated": True,
                "is_online": True,
            },
        )
        if not created:
            if not deliver.is_activated:
                deliver.is_activated = True
                deliver.is_online = True
                deliver.save()
                self.stdout.write(f"Updated Deliver to be activated: {deliver.phone}")

        if created:
            self.stdout.write(f"Created Deliver: {deliver.phone}")
        else:
            self.stdout.write(f"Deliver already exists: {deliver.phone}")

        # --- 2. Menu Creation ---

        # Dishes
        dishes_data = [
            {
                "name": "Homemade Burger",
                "description": "Juicy beef burger with cheese and fresh vegetables.",
                "price": 12.50,
                "category": "dish",
                "country": "USA",
                "photo": "dishes/default_burger.jpg",
            },
            {
                "name": "Caesar Salad",
                "description": "Fresh romaine lettuce with parmesan and croutons.",
                "price": 8.00,
                "category": "starter",
                "country": "Italy",
                "photo": "dishes/default_salad.jpg",
            },
            {
                "name": "Chocolate Cake",
                "description": "Rich dark chocolate cake.",
                "price": 6.50,
                "category": "dessert",
                "country": "France",
                "photo": "dishes/default_cake.jpg",
            },
        ]

        created_dishes = []
        for dish_data in dishes_data:
            photo = dish_data.pop("photo", None)
            dish, created = DishModel.objects.get_or_create(
                name=dish_data["name"],
                cooker=cooker,
                defaults={**dish_data, "is_enabled": True},
            )
            created_dishes.append(dish)
            if created:
                if photo:
                    DishImageModel.objects.get_or_create(dish=dish, key=photo, is_primary=True, position=0)

                # Default nutritional info
                DishNutritionalInfo.objects.get_or_create(
                    dish=dish,
                    defaults={
                        "calories": random.randint(100, 500),
                        "fats": random.randint(5, 30),
                        "proteins": random.randint(5, 40),
                        "carbohydrates": random.randint(10, 80),
                    },
                )
                self.stdout.write(f"Created Dish: {dish.name}")

        # Drinks
        drinks_data = [
            {
                "name": "Coca Cola",
                "description": "Refreshing soft drink.",
                "price": 2.50,
                "unit": "centiliters",
                "capacity": 33,
                "country": "USA",
                "photo": "drinks/default_coke.jpg",
            },
            {
                "name": "Red Wine",
                "description": "Full-bodied red wine.",
                "price": 4.00,
                "unit": "centiliters",
                "capacity": 75,
                "country": "France",
                "photo": "drinks/default_wine.jpg",
            },
        ]

        created_drinks = []
        for drink_data in drinks_data:
            photo = drink_data.pop("photo", None)
            drink, created = DrinkModel.objects.get_or_create(
                name=drink_data["name"],
                cooker=cooker,
                defaults={**drink_data, "is_enabled": True},
            )
            created_drinks.append(drink)
            if created:
                if photo:
                    DrinkImageModel.objects.get_or_create(drink=drink, key=photo, is_primary=True, position=0)

                # Default nutritional info
                DrinkNutritionalInfo.objects.get_or_create(
                    drink=drink,
                    defaults={
                        "calories": random.randint(20, 150),
                        "fats": random.randint(0, 5),
                        "proteins": random.randint(0, 5),
                        "carbohydrates": random.randint(5, 30),
                        "sugars": random.randint(5, 25),
                    },
                )

                # Default ingredients
                if "coca" in drink.name.lower():
                    ing, _ = IngredientDrinkModel.objects.get_or_create(
                        code="sucre", defaults={"name": "Sucre", "is_allergen": False}
                    )
                    drink.ingredients.add(ing)
                else:
                    ing, _ = IngredientDrinkModel.objects.get_or_create(
                        code="sulfites",
                        defaults={"name": "Sulfites", "is_allergen": True},
                    )
                    drink.ingredients.add(ing)

                self.stdout.write(f"Created Drink: {drink.name}")

        # --- 3. Orders Generation ---

        # Only generating orders if we have menu items
        if not created_dishes:
            created_dishes = list(DishModel.objects.filter(cooker=cooker))
        if not created_drinks:
            created_drinks = list(DrinkModel.objects.filter(cooker=cooker))

        if not created_dishes:
            self.stdout.write("No dishes available, skipping order generation.")
            return

        # Define order scenarios
        now = timezone.now()
        scenarios = [
            # Past Orders (Completed/Delivered)
            {
                "status": OrderStatusEnum.COMPLETED,
                "date": now - timedelta(days=1),
                "count": 15,
            },
            {
                "status": OrderStatusEnum.COMPLETED,
                "date": now - timedelta(days=7),
                "count": 10,
            },
            {
                "status": OrderStatusEnum.COMPLETED,
                "date": now - timedelta(days=30),
                "count": 15,
            },
            # Active Orders
            {"status": OrderStatusEnum.PENDING, "date": now, "count": 5},
            {"status": OrderStatusEnum.ACCEPTED, "date": now, "count": 5},
            {"status": OrderStatusEnum.DELIVERING, "date": now, "count": 5},
            # Cancelled Orders
            {
                "status": OrderStatusEnum.CANCELLED,
                "date": now - timedelta(days=2),
                "count": 5,
            },
            {
                "status": OrderStatusEnum.CANCELLED,
                "date": now - timedelta(days=3),
                "count": 5,
            },
        ]

        total_orders_created = 0
        customer_address = AddressModel.objects.filter(customer=customer).first()

        for scenario in scenarios:
            for _ in range(cast(int, scenario["count"])):
                if OrderModel.objects.filter(cooker=cooker).count() > 50:
                    break

                order = OrderModel.objects.create(
                    cooker=cooker,
                    customer=customer,
                    address=customer_address,
                    delivery_man=(
                        deliver
                        if scenario["status"] in [OrderStatusEnum.DELIVERING, OrderStatusEnum.COMPLETED]
                        else None
                    ),
                    status=scenario["status"],
                    delivery_fees=5.0,
                    delivery_distance=2.5,
                    created=scenario["date"],
                    modified=scenario["date"],
                )

                OrderModel.objects.filter(id=order.id).update(created=scenario["date"], modified=scenario["date"])

                # Add Items
                # 1-3 Random Dishes
                selected_dishes = random.sample(created_dishes, k=min(len(created_dishes), random.randint(1, 3)))
                for dish in selected_dishes:
                    OrderDishItemModel.objects.create(order=order, dish=dish, dish_quantity=random.randint(1, 2))

                # 0-2 Random Drinks
                if created_drinks:
                    selected_drinks = random.sample(created_drinks, k=min(len(created_drinks), random.randint(0, 2)))
                    for drink in selected_drinks:
                        OrderDrinkItemModel.objects.create(
                            order=order,
                            drink=drink,
                            drink_quantity=random.randint(1, 2),
                        )

                total_orders_created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeding completed. {total_orders_created} orders created."))
