from cooker_app import views as cooker_app_views
from customer_app import views as customer_app_views
from delivery_app import views as delivery_app_views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"cookers", cooker_app_views.CookerView, basename="cookers")
router.register(
    r"cookers-dashboard",
    cooker_app_views.DashboardView,
    basename="cookers-dashboard",
)
router.register(r"dishes", cooker_app_views.DishView, basename="dishes")
router.register(r"drinks", cooker_app_views.DrinkView, basename="drinks")
router.register(r"customers", customer_app_views.CustomerView, basename="customers")
router.register(r"customers-dishes", customer_app_views.DishView)
router.register(r"customers-dishes-countries", customer_app_views.DishCountriesView)
router.register(r"customers-drinks", customer_app_views.DrinkView)
router.register(r"customers-desserts", customer_app_views.DessertView)
router.register(r"customers-starters", customer_app_views.StarterView)
router.register(
    r"customers-addresses",
    customer_app_views.AddressView,
    basename="addresses",
)
router.register(
    r"customers-orders",
    customer_app_views.OrderView,
    basename="orders",
)
router.register(
    r"customers-orders-history",
    customer_app_views.HistoryOrderView,
    basename="orders-history",
)
router.register(
    r"delivers",
    delivery_app_views.DeliverView,
    basename="delivers",
)
router.register(
    r"delivers-stats",
    delivery_app_views.DeliveryOrderStatsView,
    basename="delivers-stats",
)
router.register(
    r"delivers-history",
    delivery_app_views.DeliveryHistoryView,
    basename="delivers-history",
)
# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/v1/", include(router.urls)),
    path(
        "api/v1/token/",
        cooker_app_views.TokenObtainPairWithoutPasswordView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/token/refresh/",
        cooker_app_views.TokenObtainRefreshWithoutPasswordView.as_view(),
        name="token_refresh",
    ),
    path(
        "api/v1/stripe/webhook/",
        customer_app_views.StripeWebhookView.as_view({"post": "create"}),
        name="stripe_webhook",
    ),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()  # type: ignore
