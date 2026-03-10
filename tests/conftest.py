import pytest

from config import setup_config


@pytest.fixture(scope="session", autouse=True)
def shared_config():
    """
    Populate the global config dict from environment variables.
    Runs once at the start of the test session.
    """
    setup_config()
