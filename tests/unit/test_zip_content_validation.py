"""
Covers finding [21]: "Operator uploaded log object is not constrained to ZIP content
before distribution". Non-ZIP/truncated uploads must not be turned into a download
link + team notification.
"""

import io
import zipfile
from unittest import mock

from tests.unit._lambda_loader import load_lambda_module

MODULE_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-download/files/lambda-log-download.py"
)

ENV = {
    "DOWNLOAD_DOMAIN": "download.example.gov.uk",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_TEMPLATE_ID": "template-id",
    "DOWNLOAD_TRACKING_TABLE": "download-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
    "DOWNLOAD_LINK_EXPIRY_DAYS": "7",
    "ALERTS_TEAM_EMAILS": "alerts@example.gov.uk",
}


def _load():
    return load_lambda_module(MODULE_PATH, f"lambda_log_download_{id(object())}", env=ENV)


def _make_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.log", "some log content")
    return buf.getvalue()


def _mock_s3_object(module, content: bytes):
    module.s3.head_object.return_value = {"ContentLength": len(content)}

    def _get_object(Bucket, Key, Range):
        start, end = (int(part) for part in Range.replace("bytes=", "").split("-"))
        body = mock.MagicMock()
        body.read.return_value = content[start:end + 1]
        return {"Body": body}

    module.s3.get_object.side_effect = _get_object


BUCKET = "actual-content-bucket"


def test_valid_zip_content_is_accepted():
    module = _load()
    _mock_s3_object(module, _make_zip_bytes())

    assert module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip") is True


def test_plain_text_content_is_rejected():
    module = _load()
    _mock_s3_object(module, b"just some plain text, definitely not a zip file at all")

    assert module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip") is False


def test_truncated_content_with_valid_header_but_no_eocd_is_rejected():
    """A file that merely starts with the ZIP local-file-header signature but has no
    End-Of-Central-Directory record is not a genuine archive."""
    module = _load()
    _mock_s3_object(module, b"PK\x03\x04" + b"\x00" * 40)

    assert module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip") is False


def test_empty_object_is_rejected():
    module = _load()
    _mock_s3_object(module, b"")

    assert module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip") is False


def test_is_zip_content_reads_from_the_bucket_named_in_the_event_not_a_hardcoded_one():
    """Regression test: the bucket to inspect must come from the triggering S3 event
    record, not a fixed/env-configured bucket name — the object may not live in the
    bucket a LOG_BUCKET-style env var assumes."""
    module = _load()
    _mock_s3_object(module, _make_zip_bytes())

    module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip")

    module.s3.head_object.assert_called_once_with(
        Bucket=BUCKET, Key="received/logs/x/CBC_x_MNO1.zip"
    )
    for call in module.s3.get_object.call_args_list:
        assert call.kwargs["Bucket"] == BUCKET


def test_lambda_handler_skips_non_zip_upload_and_generates_no_download_link():
    module = _load()
    _mock_s3_object(module, b"not a zip")

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": BUCKET},
                    "object": {"key": "received/logs/alert-1/CBC_alert-1_MNO1.zip"},
                }
            }
        ]
    }

    module.lambda_handler(event, None)

    module.ddb.put_item.assert_not_called()
    module.lambda_cli.invoke.assert_not_called()


def test_lambda_handler_generates_download_link_for_valid_zip():
    module = _load()
    _mock_s3_object(module, _make_zip_bytes())
    module.ddb.get_item.return_value = {"Item": {}}

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": BUCKET},
                    "object": {"key": "received/logs/alert-1/CBC_alert-1_MNO1.zip"},
                }
            }
        ]
    }

    module.lambda_handler(event, None)

    module.ddb.put_item.assert_called_once()
    module.lambda_cli.invoke.assert_called_once()
    module.s3.head_object.assert_called_once_with(
        Bucket=BUCKET, Key="received/logs/alert-1/CBC_alert-1_MNO1.zip"
    )
