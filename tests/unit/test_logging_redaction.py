"""
Asserts sensitive fields (recipient emails, MNO portal identifiers) never
appear verbatim in log output, only their masked form.
"""

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
DOWNLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-uploaded-logs-notifier/files/uploaded-logs-notifier.py"
)
UPLOAD_ENV = {
    "UPLOAD_DOMAIN": "upload.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_LOG_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
}

DOWNLOAD_ENV = {
    "GDS_AWS_PROFILE": "emergency-alerts-test",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
    "ALERTS_TEAM_EMAILS": "alerts@example.gov.uk",
}

SENSITIVE_EMAIL = "mno-contact@example.gov.uk"
PORTAL_ID = "A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6"


def _log_text(caplog) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_upload_invite_send_masks_recipient_email(caplog):
    module = load_lambda_module(UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV)

    with caplog.at_level("INFO"), mock.patch("boto3.client", side_effect=lambda *a, **k: mock.MagicMock()):
        module.send_invite(SENSITIVE_EMAIL, "broadcast-1", "Test MNO", "MNO1")

    log_text = _log_text(caplog)
    assert SENSITIVE_EMAIL not in log_text
    assert "m***@example.gov.uk" in log_text


def test_download_link_send_masks_recipient_email(caplog):
    module = load_lambda_module(DOWNLOAD_HANDLER_PATH, f"uploaded_logs_notifier_{id(object())}", env=DOWNLOAD_ENV)
    module.recipients = [SENSITIVE_EMAIL]
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "Test MNO"}, "AlertTime": {"S": ""}}}

    with caplog.at_level("INFO"):
        module.send_notification(
            "broadcast-1", "MNO1", "log-bucket", "received/logs/broadcast-1/CBC_MNO1_20250101-0000Z_broadcast-1.zip"
        )

    log_text = _log_text(caplog)
    assert SENSITIVE_EMAIL not in log_text
    assert "m***@example.gov.uk" in log_text


def test_mask_email_helper():
    module = load_lambda_module(UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV)
    assert module._mask_email("a@b.gov.uk") == "a***@b.gov.uk"
    assert module._mask_email("not-an-email") == "***"


def test_upload_edge_unknown_link_log_masks_portal_id(caplog):
    module = load_lambda_module(EDGE_UPLOAD_PATH, f"edge_log_upload_{id(object())}", env={})
    module.ddb.get_item.return_value = {}

    with caplog.at_level("WARNING"):
        item, err = module._validate_request(PORTAL_ID, "broadcast-1")

    assert item is None
    assert err is not None
    log_text = _log_text(caplog)
    assert PORTAL_ID not in log_text
    assert "A1B2***" in log_text


def test_upload_edge_confirmed_upload_log_masks_portal_id(caplog):
    module = load_lambda_module(EDGE_UPLOAD_PATH, f"edge_log_upload_{id(object())}", env={})
    module.ddb.update_item.return_value = {}
    uri = "/received/logs/broadcast-1/CBC_EE_20250512-0900Z_broadcast-1.zip"
    request = {"uri": uri, "headers": {"x-upload-token": [{"key": "X-Upload-Token", "value": PORTAL_ID}]}}

    with caplog.at_level("INFO"):
        module._handle_origin_response(request, {"status": "200"})

    log_text = _log_text(caplog)
    assert PORTAL_ID not in log_text
    assert "A1B2***" in log_text


def test_invite_registration_log_masks_portal_id(caplog):
    module = load_lambda_module(UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV)
    module.ddb.put_item.return_value = {}

    with caplog.at_level("INFO"):
        assert module.register_upload_reference(
            PORTAL_ID, "broadcast-1", "/received/logs/x.zip", "ee", "2025-05-12T09:00:00Z"
        )

    log_text = _log_text(caplog)
    assert PORTAL_ID not in log_text
    assert "A1B2***#broadcast-1" in log_text


def test_mask_portal_id_helper():
    module = load_lambda_module(EDGE_UPLOAD_PATH, f"edge_log_upload_{id(object())}", env={})
    assert module._mask_portal_id(PORTAL_ID) == "A1B2***"
    assert module._mask_portal_id("SHORT") == "***"
    assert module._mask_portal_id("") == "***"
    assert module._mask_key(f"{PORTAL_ID}#broadcast-1") == "A1B2***#broadcast-1"
