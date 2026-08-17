import os
import json
import logging
from datetime import datetime
import boto3
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GDS_AWS_PROFILE = os.environ["GDS_AWS_PROFILE"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_TEMPLATE_ID"]
LOG_INVITE_TRACKING_TABLE = os.environ["LOG_INVITE_TRACKING_TABLE"]

raw_list = os.environ["ALERTS_TEAM_EMAILS"]
recipients = [email.strip() for email in raw_list.split(",") if email.strip()]

ddb = boto3.client("dynamodb")
lambda_cli = boto3.client("lambda")
s3 = boto3.client("s3")

KEY_RE = re.compile(
    r"^received/logs/(?P<alert>[^/]+)/CBC_(?P<mno>[^_]+)_[^_]+_(?P=alert)\.zip$"
)

ZIP_HEADER_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06")
EOCD_SIGNATURE = b"PK\x05\x06"
# EOCD record is 22 bytes plus up to a 65535-byte comment.
MAX_EOCD_SEARCH_WINDOW = 22 + 65535


def _s3_read_range(bucket: str, key: str, range_str: str) -> bytes | None:
    try:
        return s3.get_object(Bucket=bucket, Key=key, Range=range_str)["Body"].read()
    except Exception as e:
        logger.error("Failed to read %s from %s/%s: %s", range_str, bucket, key, e)
        return None


def _is_zip_content(bucket: str, key: str) -> bool:
    """
    Validate the object looks like a genuine ZIP archive: a leading local/empty-archive
    file header signature, plus an End Of Central Directory record near the tail of the
    file.
    """
    try:
        size = s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
    except Exception as e:
        logger.error("Failed to read object metadata for %s/%s: %s", bucket, key, e)
        return False
    if size < len(EOCD_SIGNATURE):
        return False

    header = _s3_read_range(bucket, key, "bytes=0-3")
    if header is None or not header.startswith(ZIP_HEADER_SIGNATURES):
        return False

    tail_start = max(0, size - MAX_EOCD_SEARCH_WINDOW)
    tail = _s3_read_range(bucket, key, f"bytes={tail_start}-{size - 1}")
    return tail is not None and EOCD_SIGNATURE in tail


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    masked_local = f"{local[0]}***" if local else "***"
    return f"{masked_local}@{domain}"


def _get_upload_record(mno_label: str, broadcast_id: str) -> dict:
    """
    Fetch MnoName and AlertTime from the invite tracking record.
    """
    key = f"{mno_label}#{broadcast_id}"
    try:
        resp = ddb.get_item(
            TableName=LOG_INVITE_TRACKING_TABLE,
            Key={"AlertRef": {"S": key}}
        )
        item = resp.get("Item", {})
        mno_name = item.get("MnoName", {}).get("S") or mno_label
        alert_time = item.get("AlertTime", {}).get("S") or ""
        return {"mno_name": mno_name, "alert_time": alert_time}
    except Exception as e:
        logger.warning("Could not look up invite record for %s: %s", key, e)
        return {"mno_name": mno_label, "alert_time": ""}


def _format_alert_time(iso_str: str) -> str:
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%-d %B %Y at %H:%M UTC")
    except ValueError:
        return iso_str


def send_notification(broadcast_id: str, mno_label: str, bucket: str, key: str):
    record = _get_upload_record(mno_label, broadcast_id)
    mno_name = record["mno_name"]
    alert_time = _format_alert_time(record["alert_time"])

    filename = key.rsplit("/", 1)[-1]
    gds_cli_command = f"gds aws {GDS_AWS_PROFILE} aws s3 cp s3://{bucket}/{key} {filename}"

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
        logger.info(
            "Sent download notification for %s/%s to %s", broadcast_id, mno_name, _mask_email(email)
        )


def lambda_handler(event, context):
    """
    Triggered by S3 PutObject on received/logs/... .zip.
    """
    for rec in event["Records"]:
        bucket = rec["s3"]["bucket"]["name"]
        key = rec["s3"]["object"]["key"]
        m = KEY_RE.match(key)
        if not m:
            logger.warning("S3 key did not match expected pattern: %s", key)
            continue

        broadcast_id = m.group("alert")
        mno_label = m.group("mno")

        if not _is_zip_content(bucket, key):
            logger.warning(
                "Rejected upload with non-ZIP content for broadcast_id=%s, mno=%s",
                broadcast_id, mno_label
            )
            continue

        logger.info("New logs for broadcast_id=%s, mno=%s", broadcast_id, mno_label)

        send_notification(broadcast_id, mno_label, bucket, key)

    return {"status": "ok"}
