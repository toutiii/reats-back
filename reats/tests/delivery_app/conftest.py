import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    fixtures = [
        "addresses",
        "customers",
        "cookers",
        "delivers",
        "dishes",
        "drinks",
        "orders",
        "order_items",
    ]

    with django_db_blocker.unblock():
        call_command("loaddata", *fixtures)


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"


@pytest.fixture(scope="session")
def path() -> str:
    return "/api/v1/delivers/"


@pytest.fixture(scope="session")
def otp_verify_path() -> str:
    return "/api/v1/delivers/otp-verify/"


@pytest.fixture(scope="session")
def auth_path() -> str:
    return "/api/v1/delivers/auth/"


@pytest.fixture(scope="session")
def otp_path() -> str:
    return "/api/v1/delivers/otp/ask/"


@pytest.fixture(scope="session")
def refresh_token_path() -> str:
    return "/api/v1/token/refresh/"


@pytest.fixture(scope="session")
def delivery_stats_path() -> str:
    return "/api/v1/delivers-stats/"
