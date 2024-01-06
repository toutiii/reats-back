import pytest


@pytest.fixture(scope="session")
def path() -> str:
    return "/api/v1/cookers/"


@pytest.fixture(scope="session")
def otp_verify_path() -> str:
    return "/api/v1/cookers/otp-verify/"


@pytest.fixture(scope="session")
def auth_path() -> str:
    return "/api/v1/cookers/auth/"


@pytest.fixture(scope="session")
def otp_path() -> str:
    return "/api/v1/cookers/otp/ask/"


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"
