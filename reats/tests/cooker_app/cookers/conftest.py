import pytest


@pytest.fixture
def path() -> str:
    return "/api/v1/cookers/"


@pytest.fixture
def otp_verify_path() -> str:
    return "/api/v1/cookers/otp-verify/"
