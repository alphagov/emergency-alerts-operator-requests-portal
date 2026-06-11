import os
import json
import logging
from datetime import datetime, timezone
import boto3
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOG_BUCKET = os.environ["LOG_BUCKET"]
GDS_AWS_PROFILE = os.environ["GDS_AWS_PROFILE"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_TEMPLATE_ID"]
LOG_UPLOAD_TRACKING_TABLE = os.environ["LOG_UPLOAD_TRACKING_TABLE"]

raw_list = os.environ["ALERTS_TEAM_EMAILS"]
recipients = [email.strip() for email in raw_list.split(",") if email.strip()]

ddb = boto3.client("dynamodb")
lambda_cli = boto3.client("lambda")

KEY_RE = re.compile(
    r"^received/logs/(?P<alert>[^/]+)/CBC_(?P=alert)_(?P<mno>[^.]+)\.zip$"
)


def _get_upload_record(portal_id: str, broadcast_id: str) -> dict:
    """
    Fetch MnoName and AlertTime from the upload tracking record.
    Returns a dict with 'mno_name' and 'alert_time', falling back to safe defaults.
    """
    key = f"{portal_id}#{broadcast_id}"
    try:
        resp = ddb.get_item(
            TableName=LOG_UPLOAD_TRACKING_TABLE,
            Key={"RequestId": {"S": key}}
        )
        item = resp.get("Item", {})
        mno_name = item.get("MnoName", {}).get("S") or portal_id
        alert_time = item.get("AlertTime", {}).get("S") or ""
        return {"mno_name": mno_name, "alert_time": alert_time}
    except Exception as e:
        logger.warning("Could not look up upload record for %s: %s", key, e)
        return {"mno_name": portal_id, "alert_time": ""}


def _format_alert_time(iso_str: str) -> str:
    """Format an ISO 8601 timestamp into a human-readable string."""
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%-d %B %Y at %H:%M UTC")
    except ValueError:
        return iso_str


def send_notification(broadcast_id: str, portal_id: str):
    record = _get_upload_record(portal_id, broadcast_id)
    mno_name = record["mno_name"]
    alert_time = _format_alert_time(record["alert_time"])

    s3_key = f"received/logs/{broadcast_id}/CBC_{broadcast_id}_{portal_id}.zip"
    gds_cli_command = (
        f"gds aws {GDS_AWS_PROFILE} -- "
        f"aws s3 cp s3://{LOG_BUCKET}/{s3_key} ."
    )

    for email in recipients:
        payload = {
            "email_address": email,
            "template_id": NOTIFY_TEMPLATE_ID,
            "personalisation": {
                "broadcastId": broadcast_id,
                "MNO": mno_name,
                "alertTime": alert_time,
                "gdsCliDownloadCommand": gds_cli_command
            }
        }
        lambda_cli.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8")
        )
        logger.info("Sent download notification for %s/%s to %s", broadcast_id, mno_name, email)


def lambda_handler(event, context):
    """
    Triggered by S3 PutObject on received/logs/... .zip.
    """
    for rec in event["Records"]:
        key = rec["s3"]["object"]["key"]
        m = KEY_RE.match(key)
        if not m:
            logger.warning("S3 key did not match expected pattern: %s", key)
            continue

        broadcast_id = m.group("alert")
        portal_id = m.group("mno")
        logger.info("New logs for broadcast_id=%s, portal_id=%s", broadcast_id, portal_id)

        send_notification(broadcast_id, portal_id)

    return {"status": "ok"}
