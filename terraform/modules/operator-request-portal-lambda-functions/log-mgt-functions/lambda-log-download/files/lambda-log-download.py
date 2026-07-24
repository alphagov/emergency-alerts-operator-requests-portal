import os
import json
import base64
import uuid
import logging
from datetime import datetime, timedelta
import boto3
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DOWNLOAD_DOMAIN = os.environ["DOWNLOAD_DOMAIN"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_TEMPLATE_ID"]
DOWNLOAD_TRACKING_TABLE = os.environ["DOWNLOAD_TRACKING_TABLE"]
LOG_UPLOAD_TRACKING_TABLE = os.environ["LOG_UPLOAD_TRACKING_TABLE"]
DOWNLOAD_LINK_EXPIRY_DAYS = int(os.environ["DOWNLOAD_LINK_EXPIRY_DAYS"])

raw_list = os.environ["ALERTS_TEAM_EMAILS"]
recipients = [email.strip() for email in raw_list.split(",") if email.strip()]

ddb = boto3.client("dynamodb")
lambda_cli = boto3.client("lambda")
s3 = boto3.client("s3")

KEY_RE = re.compile(
    r"^received/logs/(?P<alert>[^/]+)/CBC_(?P=alert)_(?P<mno>[^.]+)\.zip$"
)

ZIP_HEADER_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06")
EOCD_SIGNATURE = b"PK\x05\x06"
# EOCD record is 22 bytes plus up to a 65535-byte comment.
MAX_EOCD_SEARCH_WINDOW = 22 + 65535


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

    try:
        header = s3.get_object(Bucket=bucket, Key=key, Range="bytes=0-3")["Body"].read()
    except Exception as e:
        logger.error("Failed to read object header for %s/%s: %s", bucket, key, e)
        return False
    if not header.startswith(ZIP_HEADER_SIGNATURES):
        return False

    tail_start = max(0, size - MAX_EOCD_SEARCH_WINDOW)
    try:
        tail = s3.get_object(
            Bucket=bucket, Key=key, Range=f"bytes={tail_start}-{size - 1}"
        )["Body"].read()
    except Exception as e:
        logger.error("Failed to read object tail for %s/%s: %s", bucket, key, e)
        return False
    return EOCD_SIGNATURE in tail


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    masked_local = f"{local[0]}***" if local else "***"
    return f"{masked_local}@{domain}"


def _get_mno_name(portal_id: str, broadcast_id: str) -> str:
    """
    Look up the MNO name from the upload tracking record.
    Falls back to portal_id if the record or field is not found.
    """
    key = f"{portal_id}#{broadcast_id}"
    try:
        resp = ddb.get_item(
            TableName=LOG_UPLOAD_TRACKING_TABLE,
            Key={"RequestId": {"S": key}}
        )
        name = resp.get("Item", {}).get("MnoName", {}).get("S")
        if name:
            return name
        logger.warning("No MnoName in upload tracking record for %s", key)
    except Exception as e:
        logger.warning("Could not look up MNO name for %s: %s", key, e)
    return portal_id


def generate_download_link(alert: str, mno: str) -> str:
    now = datetime.utcnow()
    expiry = now + timedelta(days=DOWNLOAD_LINK_EXPIRY_DAYS)
    expiry_str = expiry.strftime("%Y%m%d%H%M")

    token_id = uuid.uuid4().hex
    reference = f"{alert}-{token_id}"

    params = (
        f"alert={alert}"
        f"&mno={mno}"
        f"&expiry={expiry_str}"
        f"&reference={reference}"
    )
    raw_b64 = base64.urlsafe_b64encode(params.encode()).decode()

    ddb.put_item(
        TableName=DOWNLOAD_TRACKING_TABLE,
        Item={
            "RequestId": {"S": reference},
            "CreatedAt": {"S": now.isoformat()},
            "Used": {"BOOL": False},
            "RawDownloadToken": {"S": raw_b64}
        }
    )

    return raw_b64


def send_notification(broadcast_id: str, portal_id: str, download_link: str):
    mno_name = _get_mno_name(portal_id, broadcast_id)

    file_path = f"/CBC_{broadcast_id}_{portal_id}.zip"
    full_download_url = (
        f"https://{DOWNLOAD_DOMAIN}"
        f"/download/logs/{broadcast_id}"
        f"{file_path}?data={download_link}"
    )

    for email in recipients:
        payload = {
            "email_address": email,
            "template_id": NOTIFY_TEMPLATE_ID,
            "personalisation": {
                "broadcastRef": broadcast_id,
                "MNO": mno_name,
                "downloadSite": f"https://{DOWNLOAD_DOMAIN}/download.html",
                "downloadLink": full_download_url
            }
        }
        lambda_cli.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8")
        )
        logger.info(
            "Sent download link for %s/%s to %s", broadcast_id, mno_name, _mask_email(email)
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
        portal_id = m.group("mno")

        if not _is_zip_content(bucket, key):
            logger.warning(
                "Rejected upload with non-ZIP content for broadcast_id=%s, portal_id=%s",
                broadcast_id, portal_id
            )
            continue

        logger.info("New logs for broadcast_id=%s, portal_id=%s", broadcast_id, portal_id)

        token = generate_download_link(broadcast_id, portal_id)
        send_notification(broadcast_id, portal_id, token)

    return {"status": "ok"}
