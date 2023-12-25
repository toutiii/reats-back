from cooker_app import views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r"cookers", views.CookerView, basename="cookers")
router.register(r"dishes", views.DishView, basename="dishes")
router.register(r"drinks", views.DrinkView, basename="drinks")


# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/v1/", include(router.urls)),
    path(
        "api/v1/token/",
        views.TokenObtainPairWithoutPasswordView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()  # type: ignore
