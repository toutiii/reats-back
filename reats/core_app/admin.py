from django.contrib import admin

from core_app.models import (
    AddressModel,
    CookerModel,
    CustomerModel,
    DeliverModel,
    DishModel,
    DishRatingModel,
    DrinkModel,
    DrinkRatingModel,
    OrderDishItemModel,
    OrderDrinkItemModel,
    OrderModel,
)


@admin.register(CookerModel)
class CookerAdmin(admin.ModelAdmin):
    readonly_fields = ("acceptance_rate", "last_acceptance_rate_update_date")


@admin.register(DeliverModel)
class DeliverAdmin(admin.ModelAdmin):
    readonly_fields = ("grades",)


@admin.register(CustomerModel)
class CustomerAdmin(admin.ModelAdmin):
    readonly_fields = ("stripe_id",)


@admin.register(OrderModel)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = (
        "delivery_fees",
        "delivery_fees_bonus",
        "delivery_distance",
        "delivery_initial_distance",
        "paid_date",
        "processing_date",
        "completed_date",
        "delivery_in_progress_date",
        "cancelled_date",
        "delivered_date",
        "stripe_payment_intent_id",
        "stripe_payment_intent_secret",
    )


# Basic registration for other models
admin.site.register(DishModel)
admin.site.register(DrinkModel)
admin.site.register(AddressModel)
admin.site.register(OrderDishItemModel)
admin.site.register(OrderDrinkItemModel)
admin.site.register(DishRatingModel)
admin.site.register(DrinkRatingModel)
