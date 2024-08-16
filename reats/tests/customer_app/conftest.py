import pytest


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"


@pytest.fixture(scope="session")
def path() -> str:
    return "/api/v1/customers/"


@pytest.fixture(scope="session")
def otp_verify_path() -> str:
    return "/api/v1/customers/otp-verify/"


@pytest.fixture(scope="session")
def auth_path() -> str:
    return "/api/v1/customers/auth/"


@pytest.fixture(scope="session")
def otp_path() -> str:
    return "/api/v1/customers/otp/ask/"


@pytest.fixture(scope="session")
def refresh_token_path() -> str:
    return "/api/v1/token/refresh/"


@pytest.fixture(scope="session")
def customer_address_path() -> str:
    return "/api/v1/customers-addresses/"


@pytest.fixture(scope="session")
def customer_dish_path() -> str:
    return "/api/v1/customers-dishes/"


@pytest.fixture(scope="session")
def customer_drink_path() -> str:
    return "/api/v1/customers-drinks/"


@pytest.fixture(scope="session")
def customer_dessert_path() -> str:
    return "/api/v1/customers-desserts/"


@pytest.fixture(scope="session")
def customer_starter_path() -> str:
    return "/api/v1/customers-starters/"


@pytest.fixture(scope="session")
def customer_order_path() -> str:
    return "/api/v1/customers-orders/"


@pytest.fixture(scope="session")
def customer_order_history_path() -> str:
    return "/api/v1/customers-orders-history/"


@pytest.fixture(scope="session")
def customer_dishes_countries_path() -> str:
    return "/api/v1/customers-dishes-countries/"
