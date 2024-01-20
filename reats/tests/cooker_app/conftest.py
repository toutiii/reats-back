import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    fixtures = ["cookers", "dishes", "drinks"]

    with django_db_blocker.unblock():
        call_command("loaddata", *fixtures)


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"


@pytest.fixture(autouse=True)
def cooker_app_api_key(settings) -> None:
    settings.COOKER_APP_API_KEY = "some-api-key"


@pytest.fixture
def api_key_header(settings) -> dict:
    return {
        "HTTP_X-Api-Key": settings.COOKER_APP_API_KEY,
        "HTTP_App-Origin": "cooker",
    }
