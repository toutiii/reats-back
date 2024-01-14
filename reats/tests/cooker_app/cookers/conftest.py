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


@pytest.fixture(scope="session")
def refresh_token_path() -> str:
    return "/api/v1/token/refresh/"


@pytest.fixture(autouse=True)
def cooker_app_api_key(settings) -> None:
    settings.COOKER_APP_API_KEY = "some-api-key"


@pytest.fixture
def api_key_header(settings) -> dict:
    return {
        "HTTP_X-Api-Key": settings.COOKER_APP_API_KEY,
        "HTTP_App-Origin": "cooker",
    }
