"""
Asserts sensitive fields (recipient emails) never appear verbatim in
log output, only their masked form.
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
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "Test MNO"}, "AlertTime": {"S": ""}}}

    with caplog.at_level("INFO"):
        module.send_notification(
            "broadcast-1", "MNO1", "log-bucket",
            "received/logs/broadcast-1/CBC_MNO1_20250101-0000Z_broadcast-1.zip"
        )

    log_text = _log_text(caplog)
    assert SENSITIVE_EMAIL not in log_text
    assert "m***@example.gov.uk" in log_text


def test_mask_email_helper():
    module = load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV
    )
    assert module._mask_email("a@b.gov.uk") == "a***@b.gov.uk"
    assert module._mask_email("not-an-email") == "***"
