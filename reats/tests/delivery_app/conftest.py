import pytest
from core_app.models import DeliverModel


@pytest.fixture
def deliver_access_token(access_token_for):
    def _deliver_access_token(phone: str) -> str:
        return access_token_for(DeliverModel, phone)

    return _deliver_access_token


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


@pytest.fixture(scope="session")
def deliverer_devices_path() -> str:
    return "/api/v1/delivers-devices/"
