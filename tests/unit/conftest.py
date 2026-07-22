import pytest


@pytest.fixture(scope="session", autouse=True)
def shared_config():
    yield
