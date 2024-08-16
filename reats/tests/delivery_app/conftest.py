import pytest


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


@pytest.fixture(scope="session")
def delivery_history_path() -> str:
    return "/api/v1/delivers-history/"
