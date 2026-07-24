"""
Asserts sensitive fields (recipient emails, bearer/download
tokens) never appear verbatim in log output, only their masked form.
"""

from unittest import mock

from tests.unit._lambda_loader import load_lambda_module

UPLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-upload/files/log-upload-handler.py"
)
DOWNLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-download/files/lambda-log-download.py"
)
EDGE_DOWNLOAD_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda@edge-log-download/files/edge-log-download.py"
)

UPLOAD_ENV = {
    "LOG_BUCKET_NAME": "log-bucket",
    "UPLOAD_DOMAIN": "upload.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_LOG_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
}

DOWNLOAD_ENV = {
    "LOG_BUCKET": "log-bucket",
    "DOWNLOAD_DOMAIN": "download.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_TEMPLATE_ID": "template-id",
    "DOWNLOAD_TRACKING_TABLE": "download-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
    "DOWNLOAD_LINK_EXPIRY_DAYS": "7",
    "ALERTS_TEAM_EMAILS": "alerts@example.gov.uk",
}

SENSITIVE_EMAIL = "mno-contact@example.gov.uk"


def _log_text(caplog) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_upload_invite_send_masks_recipient_email(caplog):
    module = load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV
    )

    with caplog.at_level("INFO"), mock.patch(
        "boto3.client", side_effect=lambda *a, **k: mock.MagicMock()
    ):
        module.send_invite(SENSITIVE_EMAIL, "broadcast-1", "Test MNO", "MNO1")

    log_text = _log_text(caplog)
    assert SENSITIVE_EMAIL not in log_text
    assert "m***@example.gov.uk" in log_text


def test_download_link_send_masks_recipient_email(caplog):
    module = load_lambda_module(
        DOWNLOAD_HANDLER_PATH, f"lambda_log_download_{id(object())}", env=DOWNLOAD_ENV
    )
    module.recipients = [SENSITIVE_EMAIL]
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "Test MNO"}}}

    with caplog.at_level("INFO"):
        module.send_notification("broadcast-1", "MNO1", "dummy-download-token")

    log_text = _log_text(caplog)
    assert SENSITIVE_EMAIL not in log_text
    assert "m***@example.gov.uk" in log_text


def test_expired_download_token_log_masks_reference(caplog):
    module = load_lambda_module(
        EDGE_DOWNLOAD_PATH, f"edge_log_download_{id(object())}", env={}
    )
    reference = "alert-123-abcdef0123456789abcdef0123456789"

    with caplog.at_level("WARNING"):
        err = module._check_expiry({"expiry": "202001010000", "reference": reference})

    assert err is not None
    log_text = _log_text(caplog)
    assert reference not in log_text
    assert "alert-123-***" in log_text


def test_token_mismatch_log_masks_reference(caplog):
    module = load_lambda_module(
        EDGE_DOWNLOAD_PATH, f"edge_log_download_{id(object())}", env={}
    )
    reference = "alert-999-deadbeefdeadbeefdeadbeefdeadbeef"
    module.ddb.get_item.return_value = {"Item": {"RawDownloadToken": {"S": "expected-token"}}}

    with caplog.at_level("WARNING"):
        item, err = module._get_tracking_record(reference, "a-different-token")

    assert item is None
    assert err is not None
    log_text = _log_text(caplog)
    assert reference not in log_text
    assert "alert-999-***" in log_text


def test_download_authorized_log_does_not_include_full_reference(caplog):
    """The final 'download authorized' log line must not reprint the bearer
    reference/token — only non-secret identifiers (alert, mno, count)."""
    module = load_lambda_module(
        EDGE_DOWNLOAD_PATH, f"edge_log_download_{id(object())}", env={}
    )
    reference = "alert-1-secrettoken0123456789"
    module.ddb.get_item.return_value = {
        "Item": {"RawDownloadToken": {"S": "TOKEN"}, "DownloadCount": {"N": "0"}}
    }
    module.ddb.update_item.return_value = {}

    import base64
    from datetime import datetime, timedelta, timezone

    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d%H%M")
    params = f"alert=alert-1&mno=MNO1&expiry={expiry}&reference={reference}"
    token = base64.urlsafe_b64encode(params.encode()).decode()
    module.ddb.get_item.return_value["Item"]["RawDownloadToken"]["S"] = token

    with caplog.at_level("INFO"):
        module.lambda_handler(
            {"Records": [{"cf": {"request": {"method": "GET", "querystring": f"data={token}"}}}]},
            None,
        )

    log_text = _log_text(caplog)
    assert reference not in log_text
    assert "secrettoken" not in log_text


def test_mask_email_helper():
    module = load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV
    )
    assert module._mask_email("a@b.gov.uk") == "a***@b.gov.uk"
    assert module._mask_email("not-an-email") == "***"


def test_mask_reference_helper():
    module = load_lambda_module(
        EDGE_DOWNLOAD_PATH, f"edge_log_download_{id(object())}", env={}
    )
    assert module._mask_reference("alert-123-abcdef") == "alert-123-***"
    assert module._mask_reference("nodash") == "***"
