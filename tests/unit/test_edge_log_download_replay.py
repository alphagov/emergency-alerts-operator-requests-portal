"""
Covers finding [16]: "Operator log download tokens can be replayed until expiry
despite one-time semantics". A second GET with a copied/leaked-but-unexpired token
must be rejected once the first download has been recorded.
"""

import base64
from datetime import datetime, timedelta, timezone

from tests.unit._lambda_loader import load_lambda_module

MODULE_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda@edge-log-download/files/edge-log-download.py"
)


class _FakeConditionalCheckFailedException(Exception):
    pass


def _load():
    module = load_lambda_module(MODULE_PATH, f"edge_log_download_{id(object())}", env={})
    # ddb is a MagicMock; give it a real exception class so `except ddb.exceptions.
    # ConditionalCheckFailedException` in the source can actually match a raised error.
    module.ddb.exceptions.ConditionalCheckFailedException = _FakeConditionalCheckFailedException
    return module


def _build_token(reference: str, alert: str = "alert-1", mno: str = "MNO1") -> str:
    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d%H%M")
    params = f"alert={alert}&mno={mno}&expiry={expiry}&reference={reference}"
    return base64.urlsafe_b64encode(params.encode()).decode()


def _build_event(token: str) -> dict:
    return {
        "Records": [{"cf": {"request": {"method": "GET", "querystring": f"data={token}"}}}]
    }


def test_first_download_is_recorded_successfully():
    module = _load()
    module.ddb.update_item.return_value = {}

    err = module._increment_download("alert-1-abc123")

    assert err is None
    module.ddb.update_item.assert_called_once()
    _, kwargs = module.ddb.update_item.call_args
    assert "ConditionExpression" in kwargs


def test_replayed_token_is_rejected_with_already_used():
    module = _load()
    module.ddb.update_item.side_effect = module.ddb.exceptions.ConditionalCheckFailedException()

    err = module._increment_download("alert-1-abc123")

    assert err is not None
    assert err["status"] == "403"
    assert "already been used" in err["body"]


def test_lambda_handler_rejects_replay_of_valid_unexpired_token():
    """End-to-end: the same token used twice before expiry must succeed once and
    then be rejected, not silently accepted again."""
    module = _load()
    reference = "alert-1-abc123"
    token = _build_token(reference)
    module.ddb.get_item.return_value = {
        "Item": {"RawDownloadToken": {"S": token}, "DownloadCount": {"N": "0"}}
    }

    module.ddb.update_item.return_value = {}
    first = module.lambda_handler(_build_event(token), None)
    assert first["uri"] == "/received/logs/alert-1/CBC_alert-1_MNO1.zip"

    module.ddb.update_item.side_effect = module.ddb.exceptions.ConditionalCheckFailedException()
    second = module.lambda_handler(_build_event(token), None)

    assert second["status"] == "403"
    assert second["headers"]["x-error-type"][0]["value"] == "already_used"
