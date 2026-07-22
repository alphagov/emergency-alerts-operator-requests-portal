"""
Helper for unit-testing the Lambda/Lambda@Edge handler source files under
terraform/modules/.../files/*.py.
"""

import importlib.util
import os
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def _temporary_env(env: dict):
    sentinel = object()
    previous = {key: os.environ.get(key, sentinel) for key in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is sentinel:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def load_lambda_module(rel_path: str, module_name: str, env: dict = None) -> ModuleType:
    full_path = REPO_ROOT / rel_path
    with _temporary_env(env or {}), mock.patch(
        "boto3.client", side_effect=lambda *args, **kwargs: mock.MagicMock()
    ):
        spec = importlib.util.spec_from_file_location(module_name, full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module
