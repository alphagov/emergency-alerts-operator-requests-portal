"""
MNOs must upload within 2 days of the broadcast start, so upload links expire
UPLOAD_LINK_EXPIRY_SECONDS after the broadcast start rather than after the invite.
"""

from datetime import datetime, timedelta, timezone

from tests.unit._lambda_loader import load_lambda_module

UPLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-upload/files/log-upload-handler.py"
)

UPLOAD_ENV = {
    "UPLOAD_DOMAIN": "upload.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_LOG_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
}


def _load(env=None):
    return load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env={**UPLOAD_ENV, **(env or {})}
    )


def test_default_window_is_two_days_from_the_broadcast_start():
    module = _load()
    assert module._upload_link_expiry("2025-05-12T09:00:00Z") == datetime(2025, 5, 14, 9, 0, tzinfo=timezone.utc)


def test_window_follows_the_configured_expiry():
    module = _load({"UPLOAD_LINK_EXPIRY_SECONDS": "3600"})
    assert module._upload_link_expiry("2025-05-12T09:00:00Z") == datetime(2025, 5, 12, 10, 0, tzinfo=timezone.utc)


def test_naive_broadcast_start_is_treated_as_utc():
    module = _load()
    assert module._upload_link_expiry("2025-05-12T09:00:00") == datetime(2025, 5, 14, 9, 0, tzinfo=timezone.utc)


def test_missing_or_invalid_broadcast_start_falls_back_to_now():
    module = _load()
    for value in ("", "not-a-date", None):
        expiry = module._upload_link_expiry(value)
        assert abs(expiry - (datetime.now(timezone.utc) + timedelta(days=2))) < timedelta(seconds=5)
