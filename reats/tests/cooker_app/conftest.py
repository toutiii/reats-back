import pytest


@pytest.fixture(scope="session")
def token_path() -> str:
    return "/api/v1/token/"
