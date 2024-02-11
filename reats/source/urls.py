from cooker_app import views as cooker_app_views
from customer_app import views as customer_app_views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"cookers", cooker_app_views.CookerView, basename="cookers")
router.register(r"dishes", cooker_app_views.DishView, basename="dishes")
router.register(r"drinks", cooker_app_views.DrinkView, basename="drinks")
router.register(r"customers", customer_app_views.CustomerView, basename="customers")
router.register(r"customers-dishes", customer_app_views.DishView)


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
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()  # type: ignore
