import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    fixtures = ["cookers", "dishes"]

    with django_db_blocker.unblock():
        call_command("loaddata", *fixtures)


@pytest.fixture
def path() -> str:
    return "/api/v1/dishes/"
