from cooker_app import views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"cookers", views.CookerSignUpView, basename="cookers")
router.register(r"dishes", views.DishView, basename="dishes")

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/v1/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()  # type: ignore
