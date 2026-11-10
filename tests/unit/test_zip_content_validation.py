"""
Non-ZIP/truncated uploads must not be turned into a "logs ready" notification.
Instead the MNO's upload link is released for a re-upload and, when a template
is configured, the Alerts team is told a file was rejected.
"""

import io
import json
import zipfile
from unittest import mock

from tests.unit._lambda_loader import load_lambda_module

MODULE_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-uploaded-logs-notifier/files/uploaded-logs-notifier.py"
)

ENV = {
    "GDS_AWS_PROFILE": "emergency-alerts-test",
    "NOTIFY_LAMBDA_ARN": "arn:aws:lambda:eu-west-2:123456789012:function:notify",
    "NOTIFY_TEMPLATE_ID": "template-id",
    "LOG_INVITE_TRACKING_TABLE": "invite-tracking",
    "LOG_UPLOAD_TRACKING_TABLE": "upload-tracking",
    "ALERTS_TEAM_EMAILS": "alerts@example.gov.uk",
}


def _load():
    return load_lambda_module(MODULE_PATH, f"uploaded_logs_notifier_{id(object())}", env=ENV)


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
        body.read.return_value = content[start : end + 1]
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
    record, not a fixed/env-configured bucket name."""
    module = _load()
    _mock_s3_object(module, _make_zip_bytes())

    module._is_zip_content(BUCKET, "received/logs/x/CBC_x_MNO1.zip")

    module.s3.head_object.assert_called_once_with(Bucket=BUCKET, Key="received/logs/x/CBC_x_MNO1.zip")
    for call in module.s3.get_object.call_args_list:
        assert call.kwargs["Bucket"] == BUCKET


SELF_DESCRIPTIVE_KEY = "received/logs/alert-1/CBC_THREE_20250512-0900Z_alert-1.zip"


def test_lambda_handler_skips_non_zip_upload_and_sends_no_notification():
    module = _load()
    _mock_s3_object(module, b"not a zip")
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "three"}, "AlertTime": {"S": ""}}}

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": BUCKET},
                    "object": {"key": SELF_DESCRIPTIVE_KEY},
                }
            }
        ]
    }

    module.lambda_handler(event, None)

    module.lambda_cli.invoke.assert_not_called()


def test_lambda_handler_sends_notification_for_valid_zip():
    module = _load()
    _mock_s3_object(module, _make_zip_bytes())
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "Test MNO"}, "AlertTime": {"S": ""}}}

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": BUCKET},
                    "object": {"key": SELF_DESCRIPTIVE_KEY},
                }
            }
        ]
    }

    module.lambda_handler(event, None)

    module.lambda_cli.invoke.assert_called_once()
    module.s3.head_object.assert_called_once_with(Bucket=BUCKET, Key=SELF_DESCRIPTIVE_KEY)


UPLOAD_REQUEST_ID = "A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6#alert-1"
NON_ZIP_EVENT = {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": SELF_DESCRIPTIVE_KEY}}}]}


def test_rejected_upload_releases_the_upload_link():
    module = _load()
    _mock_s3_object(module, b"not a zip")
    module.ddb.get_item.return_value = {
        "Item": {"MnoName": {"S": "three"}, "AlertTime": {"S": ""}, "UploadRequestId": {"S": UPLOAD_REQUEST_ID}}
    }

    module.lambda_handler(NON_ZIP_EVENT, None)

    module.ddb.get_item.assert_called_once_with(TableName="invite-tracking", Key={"AlertRef": {"S": "THREE#alert-1"}})
    update = module.ddb.update_item.call_args.kwargs
    assert update["TableName"] == "upload-tracking"
    assert update["Key"] == {"RequestId": {"S": UPLOAD_REQUEST_ID}}
    assert update["ExpressionAttributeValues"] == {":false": {"BOOL": False}}


def test_rejected_upload_without_link_key_does_not_release_anything():
    module = _load()
    _mock_s3_object(module, b"not a zip")
    module.ddb.get_item.return_value = {"Item": {"MnoName": {"S": "three"}}}

    module.lambda_handler(NON_ZIP_EVENT, None)

    module.ddb.update_item.assert_not_called()


def test_rejected_upload_emails_the_alerts_team_when_a_template_is_configured():
    module = load_lambda_module(
        MODULE_PATH,
        f"uploaded_logs_notifier_{id(object())}",
        env={**ENV, "NOTIFY_REJECTED_TEMPLATE_ID": "rejected-template-id"},
    )
    _mock_s3_object(module, b"not a zip")
    module.ddb.get_item.return_value = {
        "Item": {"MnoName": {"S": "three"}, "AlertTime": {"S": ""}, "UploadRequestId": {"S": UPLOAD_REQUEST_ID}}
    }

    module.lambda_handler(NON_ZIP_EVENT, None)

    module.lambda_cli.invoke.assert_called_once()
    payload = json.loads(module.lambda_cli.invoke.call_args.kwargs["Payload"])
    assert payload["template_id"] == "rejected-template-id"
    assert payload["personalisation"]["broadcastId"] == "alert-1"
    assert payload["personalisation"]["MNO"] == "three"
