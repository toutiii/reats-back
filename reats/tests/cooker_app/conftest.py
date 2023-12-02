import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    fixtures = ["cookers", "dishes", "drinks"]

    with django_db_blocker.unblock():
        call_command("loaddata", *fixtures)
