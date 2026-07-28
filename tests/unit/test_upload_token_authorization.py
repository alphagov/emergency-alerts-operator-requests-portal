"""
Upload authorization must rely on an opaque, high-entropy, server-issued token
bound to server-side state — not on the visible mno/broadcast_id tuple.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest import mock

from tests.unit._lambda_loader import load_lambda_module

UPLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-upload/files/log-upload-handler.py"
)
EDGE_UPLOAD_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda@edge-log-upload/files/edge-log-upload.py"
)

UPLOAD_ENV = {
    "LOG_BUCKET_NAME": "log-bucket",
    "UPLOAD_DOMAIN": "upload.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_LOG_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
}

MNO_ID = "MNO1"
PORTAL_ID = "T78QW4"
BROADCAST_ID = "broadcast-123"


def _load_upload_handler():
    return load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV
    )


def _load_edge_upload():
    return load_lambda_module(EDGE_UPLOAD_PATH, f"edge_log_upload_{id(object())}", env={})


def test_generate_upload_token_is_high_entropy_and_unique():
    module = _load_upload_handler()

    tokens = {module.generate_upload_token() for _ in range(100)}

    assert len(tokens) == 100
    assert all(len(t) >= 32 for t in tokens)


def test_register_upload_reference_keys_the_ddb_item_by_token_not_identifiers():
    module = _load_upload_handler()
    token = "opaque-token-value"

    module.register_upload_reference(token, PORTAL_ID, BROADCAST_ID, "/received/logs/x.zip", MNO_ID)

    module.ddb.put_item.assert_called_once()
    _, kwargs = module.ddb.put_item.call_args
    item = kwargs["Item"]
    assert item["RequestId"] == {"S": token}
    assert f"{PORTAL_ID}#{BROADCAST_ID}" != item["RequestId"]["S"]
    # Identifiers are still recorded on the item for lookups/observability,
    # but they are not part of the bearer credential itself.
    assert item["MnoId"] == {"S": PORTAL_ID}
    assert item["BroadcastId"] == {"S": BROADCAST_ID}


def test_send_invite_url_contains_only_the_token_not_mno_or_broadcast_id():
    module = _load_upload_handler()
    captured = {}

    def _capture_invoke(FunctionName, InvocationType, Payload):
        captured["payload"] = json.loads(Payload)

    with mock.patch("boto3.client", return_value=mock.MagicMock(invoke=_capture_invoke)):
        module.send_invite("mno@example.gov.uk", "secret-token-abc", BROADCAST_ID, MNO_ID, PORTAL_ID)

    upload_site = captured["payload"]["personalisation"]["uploadSite"]
    assert "token=secret-token-abc" in upload_site
    assert "mno=" not in upload_site
    assert "broadcast_id=" not in upload_site


def test_viewer_request_rejects_missing_token():
    module = _load_edge_upload()

    req = {"method": "PUT", "querystring": ""}
    result = module._handle_viewer_request(req)

    assert result["status"] == "400"
    assert result["headers"]["x-error-type"][0]["value"] == "missing_token"


def test_viewer_request_rejects_unknown_token():
    module = _load_edge_upload()
    module.ddb.get_item.return_value = {}

    req = {"method": "PUT", "querystring": "token=does-not-exist"}
    result = module._handle_viewer_request(req)

    assert result["status"] == "403"
    assert result["headers"]["x-error-type"][0]["value"] == "invalid_request"


def test_viewer_request_rejects_the_old_guessable_mno_broadcast_id_scheme():
    module = _load_edge_upload()

    req = {"method": "PUT", "querystring": f"mno={PORTAL_ID}&broadcast_id={BROADCAST_ID}"}
    result = module._handle_viewer_request(req)

    assert result["status"] == "400"
    assert result["headers"]["x-error-type"][0]["value"] == "missing_token"
    module.ddb.get_item.assert_not_called()


def test_viewer_request_rejects_expired_token():
    module = _load_edge_upload()
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    module.ddb.get_item.return_value = {
        "Item": {
            "Used": {"BOOL": False},
            "ExpiresAt": {"S": expired},
            "S3Location": {"S": "/received/logs/x/CBC_x_MNO1.zip"},
        }
    }

    req = {"method": "PUT", "querystring": "token=some-valid-looking-token"}
    result = module._handle_viewer_request(req)

    assert result["status"] == "403"
    assert result["headers"]["x-error-type"][0]["value"] == "expired_link"


def test_viewer_request_derives_identifiers_from_the_record_not_the_client():
    """mno/broadcast_id used for logging/S3 targeting come from the trusted
    DynamoDB record looked up by token, never from client-supplied query params."""
    module = _load_edge_upload()
    module.ddb.get_item.return_value = {
        "Item": {
            "Used": {"BOOL": False},
            "S3Location": {"S": "/received/logs/real-broadcast/CBC_real-broadcast_REALMNO.zip"},
            "MnoId": {"S": "REALMNO"},
            "BroadcastId": {"S": "real-broadcast"},
        }
    }

    # Even if the querystring also carried a spoofed mno/broadcast_id, it's ignored
    # only the token is parsed and the record's own attributes are trusted.
    req = {"method": "PUT", "querystring": "token=valid-token&mno=SPOOFED&broadcast_id=spoofed-id"}
    result = module._handle_viewer_request(req)

    assert result["uri"] == "/received/logs/real-broadcast/CBC_real-broadcast_REALMNO.zip"
