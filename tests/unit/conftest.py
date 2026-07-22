import pytest


@pytest.fixture(scope="session", autouse=True)
def shared_config():
    """
    Overrides the functional-test `shared_config` fixture (tests/conftest.py) for
    everything under tests/unit/. Unit tests here load Lambda source files directly
    with mocked AWS clients and don't need real environment/credentials.
    """
    yield
