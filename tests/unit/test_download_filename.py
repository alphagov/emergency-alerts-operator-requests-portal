"""
The uploaded object itself, as stored in S3, must be self-descriptive (MNO name +
broadcast time + broadcast ID).
"""

import json
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
    "LOG_BUCKET_NAME": "log-bucket",
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

BUCKET = "content-bucket"
BROADCAST_ID = "0904c060-b8fd-4eb1-85e6-d3b29d724611"
PORTAL_ID = "f63bb184-631d-4543-91ef-ecbb28248af3"
MNO_LABEL = "THREE"


def _load_upload():
    return load_lambda_module(
        UPLOAD_HANDLER_PATH, f"log_upload_handler_{id(object())}", env=UPLOAD_ENV
    )


def _load_download():
    return load_lambda_module(
        DOWNLOAD_HANDLER_PATH, f"lambda_log_download_{id(object())}", env=DOWNLOAD_ENV
    )


def test_sanitize_and_timestamp_helpers():
    module = _load_upload()
    assert module._sanitize_for_filename("three") == "THREE"
    assert module._sanitize_for_filename("Vodafone UK!") == "VODAFONE-UK"
    assert module._sanitize_for_filename("") == "UNKNOWN"
    assert module._format_timestamp_for_filename("2025-05-12T09:00:00Z") == "20250512-0900Z"
    assert module._format_timestamp_for_filename("") == "unknown-time"


def test_upload_writes_self_descriptive_s3_key_without_portal_id_and_invite_record():
    module = _load_upload()
    module._get_mno_identifier = lambda mno_id: PORTAL_ID
    module._get_mno_emails = lambda mno_id: ["mno@example.gov.uk"]
    module.ddb.get_item.return_value = {}

    event = {
        "alert_reference": "ref-1",
        "broadcast_start": "2025-05-12T09:00:00Z",
        "mnos": [{"mno_id": "three", "provider_message_id": BROADCAST_ID}],
    }
    with mock.patch("boto3.client", side_effect=lambda *a, **k: mock.MagicMock()):
        module.lambda_handler(event, None)

    upload_calls = [
        call for call in module.ddb.put_item.call_args_list
        if call.kwargs["TableName"] == "upload-tracking"
    ]
    assert len(upload_calls) == 1
    upload_item = upload_calls[0].kwargs["Item"]
    assert upload_item["RequestId"] == {"S": f"{PORTAL_ID}#{BROADCAST_ID}"}
    assert upload_item["S3Location"] == {
        "S": f"/received/logs/{BROADCAST_ID}/CBC_{MNO_LABEL}_20250512-0900Z_{BROADCAST_ID}.zip"
    }

    invite_calls = [
        call for call in module.ddb.put_item.call_args_list
        if call.kwargs["TableName"] == "invite-tracking"
    ]
    assert len(invite_calls) == 1
    invite_item = invite_calls[0].kwargs["Item"]
    assert invite_item["AlertRef"] == {"S": f"{MNO_LABEL}#{BROADCAST_ID}"}
    assert invite_item["MnoName"] == {"S": "three"}


SELF_DESCRIPTIVE_KEY = f"received/logs/{BROADCAST_ID}/CBC_{MNO_LABEL}_20250512-0900Z_{BROADCAST_ID}.zip"


def test_gds_cli_command_reuses_the_actual_uploaded_filename():
    module = _load_download()
    module.ddb.get_item.return_value = {
        "Item": {"MnoName": {"S": "Three"}, "AlertTime": {"S": "2025-05-12T09:00:00Z"}}
    }
    captured = {}

    def _capture_invoke(FunctionName, InvocationType, Payload):
        captured["payload"] = json.loads(Payload)

    module.lambda_cli.invoke.side_effect = _capture_invoke

    module.send_notification(BROADCAST_ID, MNO_LABEL, BUCKET, SELF_DESCRIPTIVE_KEY)

    payload = captured["payload"]
    command = payload["personalisation"]["gdsCliDownloadCommand"]

    assert command == (
        f"gds aws emergency-alerts-test aws s3 cp "
        f"s3://{BUCKET}/{SELF_DESCRIPTIVE_KEY} "
        f"CBC_{MNO_LABEL}_20250512-0900Z_{BROADCAST_ID}.zip"
    )
    assert payload["personalisation"]["MNO"] == "Three"
    assert PORTAL_ID not in json.dumps(payload)


def test_gds_cli_command_falls_back_to_mno_label_not_a_uuid_if_record_missing():
    module = _load_download()
    module.ddb.get_item.return_value = {}
    captured = {}

    def _capture_invoke(FunctionName, InvocationType, Payload):
        captured["payload"] = json.loads(Payload)

    module.lambda_cli.invoke.side_effect = _capture_invoke

    module.send_notification(BROADCAST_ID, MNO_LABEL, BUCKET, SELF_DESCRIPTIVE_KEY)

    assert captured["payload"]["personalisation"]["MNO"] == MNO_LABEL
