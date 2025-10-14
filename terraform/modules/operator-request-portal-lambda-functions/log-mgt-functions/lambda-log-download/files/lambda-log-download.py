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

LOG_BUCKET = os.environ["LOG_BUCKET"]
DOWNLOAD_DOMAIN = os.environ["DOWNLOAD_DOMAIN"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_TEMPLATE_ID"]
DOWNLOAD_TRACKING_TABLE = os.environ["DOWNLOAD_TRACKING_TABLE"]
DOWNLOAD_LINK_EXPIRY_DAYS = int(os.environ["DOWNLOAD_LINK_EXPIRY_DAYS"])

raw_list = os.environ["ALERTS_TEAM_EMAILS"]
recipients = [email.strip() for email in raw_list.split(",") if email.strip()]

ddb = boto3.client("dynamodb")
lambda_cli = boto3.client("lambda")
s3 = boto3.client("s3")

# Regex to extract alert/mno from key
KEY_RE = re.compile(r"^received/logs/(?P<alert>[^/]+)/CBC_(?P=alert)_(?P<mno>[A-Z]+[0-9]+)\.zip$")


def get_original_alert_ref(safe_alert: str) -> str:
    """
    Retrieve the original alert reference from S3 folder metadata.
    Falls back to the safe_alert if metadata is not found.
    """
    try:
        # Try to get metadata from the folder object
        folder_key = f"logs/{safe_alert}/"
        response = s3.head_object(Bucket=LOG_BUCKET, Key=folder_key)
        metadata = response.get('Metadata', {})
        original_ref = metadata.get('original-alert-ref')

        if original_ref:
            logger.info(f"Retrieved original alert ref: {original_ref} for safe_alert: {safe_alert}")
            return original_ref
        else:
            logger.warning(f"No original-alert-ref metadata found for {safe_alert}")
            return safe_alert

    except Exception as e:
        logger.error(f"Error retrieving metadata for {safe_alert}: {e}")
        # Fallback: try to reverse the transformation (May not work if dashes and underscores are both present in original alert name)
        return safe_alert.replace('_', '-')


def generate_download_link(alert: str, mno: str) -> str:
    now = datetime.utcnow()
    expiry = now + timedelta(days=DOWNLOAD_LINK_EXPIRY_DAYS)
    expiry_str = expiry.strftime("%Y%m%d%H%M")

    safe_alert = re.sub(r'[^A-Za-z0-9]+', '_', alert).strip('_')
    token_id = uuid.uuid4().hex
    reference = f"{safe_alert}-{token_id}"

    params = (
        f"alert={safe_alert}"
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


def send_notification(safe_alert: str, mno: str, download_link: str):
    original_alert = get_original_alert_ref(safe_alert)

    for email in recipients:
        payload = {
            "email_address": email,
            "template_id": NOTIFY_TEMPLATE_ID,
            "personalisation": {
                "broadcastRef": original_alert,
                "MNO": mno,
                "downloadSite": f"https://{DOWNLOAD_DOMAIN}/download.html",
                "downloadLink": download_link
            }
        }
        lambda_cli.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8")
        )
        logger.info(f"Sent download link for {original_alert}/{mno} to {email}")


def lambda_handler(event, context):
    """
    Triggered by S3 PutObject on upload/logs/... .zip.
    """
    for rec in event["Records"]:
        key = rec["s3"]["object"]["key"]
        m = KEY_RE.match(key)
        if not m:
            logger.warning("S3 key did not match expected pattern: %s", key)
            continue

        safe_alert = m.group("alert")
        mno = m.group("mno")
        logger.info("New logs for safe_alert=%s, mno=%s", safe_alert, mno)

        token = generate_download_link(safe_alert, mno)
        send_notification(safe_alert, mno, token)

    return {"status": "ok"}
