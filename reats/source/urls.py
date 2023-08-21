from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .cooker_app import views

router = DefaultRouter()
router.register(r"cookers", views.CookerSignUpView, basename="cookers")

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("api/v1/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()  # type: ignore
