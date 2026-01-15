import os
import json
import base64
import uuid
import logging
from datetime import datetime, timedelta
import boto3
import urllib.parse
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOG_BUCKET = os.environ["LOG_BUCKET_NAME"]
UPLOAD_DOMAIN = os.environ["UPLOAD_DOMAIN"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_LOG_TEMPLATE_ID"]
LOG_INVITE_TRACKING_TABLE = os.environ["LOG_INVITE_TRACKING_TABLE"]
LOG_UPLOAD_TRACKING_TABLE = os.environ["LOG_UPLOAD_TRACKING_TABLE"]
EXPIRY_SECONDS = int(os.environ.get("UPLOAD_LINK_EXPIRY_SECONDS", "604800"))

ddb = boto3.client("dynamodb")


def already_invited(alert_ref: str) -> bool:
    resp = ddb.get_item(
        TableName=LOG_INVITE_TRACKING_TABLE,
        Key={"AlertRef": {"S": alert_ref}}
    )
    return "Item" in resp


def mark_invited(alert_ref: str):
    ddb.put_item(
        TableName=LOG_INVITE_TRACKING_TABLE,
        Item={
            "AlertRef": {"S": alert_ref},
            "InvitedAt": {"S": datetime.utcnow().isoformat()}
        }
    )


def register_upload_reference(reference: str, raw_token: str, original_alert_ref: str) -> bool:
    try:
        resp = ddb.get_item(
            TableName=LOG_UPLOAD_TRACKING_TABLE,
            Key={"RequestId": {"S": reference}}
        )
        if "Item" in resp:
            logger.warn(f"Reference {reference} already exists in DynamoDB")
            return False

        ddb.put_item(
            TableName=LOG_UPLOAD_TRACKING_TABLE,
            Item={
                "RequestId": {"S": reference},
                "CreatedAt": {"S": datetime.utcnow().isoformat()},
                "Used": {"BOOL": False},
                "RawToken": {"S": raw_token},
                "OriginalAlertRef": {"S": original_alert_ref}
            }
        )
        logger.info(f"Stored reference {reference} with RawToken {raw_token} and original alert {original_alert_ref}")
        return True

    except Exception as e:
        logger.error(f"Error registering reference {reference}: {e}")
        return False


def generate_upload_link(alert_ref: str, mno_id: str) -> str:
    safe_alert = re.sub(r'[^A-Za-z0-9]+', '_', alert_ref).strip('_')

    now = datetime.utcnow()
    expiry = now + timedelta(seconds=EXPIRY_SECONDS)
    expiry_str = expiry.strftime("%Y%m%d%H%M")

    token_id = uuid.uuid4().hex
    reference = f"{safe_alert}-{token_id}"

    location = f"/received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
    params = (
        f"location={location}"
        f"&type=upload"
        f"&expiry={expiry_str}"
        f"&reference={reference}"
        f"&original_alert={urllib.parse.quote(alert_ref)}"
    )
    raw_b64 = base64.urlsafe_b64encode(params.encode()).decode()

    registered = register_upload_reference(reference, raw_b64, alert_ref)
    if not registered:
        logger.error(f"Failed to register reference {reference}, retrying")
        token_id = uuid.uuid4().hex
        reference = f"{safe_alert}-{token_id}"
        raw_b64 = base64.urlsafe_b64encode(params.encode()).decode()
        register_upload_reference(reference, raw_b64, alert_ref)

    encoded_token = urllib.parse.quote(raw_b64)

    final_url = f"https://{UPLOAD_DOMAIN}/received/?data={encoded_token}"
    logger.info(f"Generated upload URL: {final_url} (ref={reference})")

    return final_url


def prepare_folder(alert_ref: str):
    try:
        s3 = boto3.client("s3")
        safe_alert = re.sub(r'[^A-Za-z0-9]+', '_', alert_ref).strip('_')
        prefix = f"logs/{safe_alert}/"

        # Store original alert reference in the folder metadata
        s3.put_object(
            Bucket=LOG_BUCKET,
            Key=prefix,
            Metadata={
                'original-alert-ref': alert_ref
            }
        )
        logger.info(f"Created S3 prefix: {prefix} with original alert ref: {alert_ref}")
    except Exception as e:
        logger.error(f"Error creating S3 prefix {prefix}: {e}")


def send_invite(email: str, upload_url: str, alert_ref: str, mno_id: str):
    try:
        token = upload_url.split("?data=", 1)[1]
    except IndexError:
        token = upload_url

    upload_site = f"https://{UPLOAD_DOMAIN}/upload-logs.html"
    payload = {
        "email_address": email,
        "template_id": NOTIFY_TEMPLATE_ID,
        "personalisation": {
            "broadcastRef": alert_ref,
            "MNO": mno_id,
            "uploadSite": upload_site,
            "oneTimeLink": token
        }
    }
    try:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8")
        )
        logger.info(f"Sent invite to {email} for MNO {mno_id}")
    except Exception as e:
        logger.error(f"Error sending invite to {email}: {e}")


def lambda_handler(event, context):
    """
    Handler for sending log-upload invites. Expects event:
    {
      "alert_reference": "ALERT123",
      "environment":     "dev",
      "broadcast_start": "2025-05-12T09:00:00Z",
      "broadcast_end":   "2025-05-12T09:15:00Z",
      "mnos": [
        { "mno_id": "MNO001", "emails": ["examplar1@digital.cabinet-office.gov.uk"] },
        { "mno_id": "MNO002", "emails": ["examplar2@digital.cabinet-office.gov.uk"] }
      ]
    }
    """
    logger.info(f"Processing upload invite event: {json.dumps(event)}")

    alert_ref = event["alert_reference"]

    if already_invited(alert_ref):
        logger.info(f"Invites for alert {alert_ref} already sent")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Invites for alert {alert_ref} already sent"
            })
        }

    prepare_folder(alert_ref)

    links_generated = []
    for mno in event.get("mnos", []):
        mno_id = mno["mno_id"]
        link = generate_upload_link(alert_ref, mno_id)
        links_generated.append({"mno_id": mno_id})

        for email in mno.get("emails", []):
            send_invite(email, link, alert_ref, mno_id)

    mark_invited(alert_ref)

    logger.info(f"Successfully sent {len(links_generated)} upload invites for alert {alert_ref}")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Log upload invites sent",
            "alert_reference": alert_ref,
            "links_generated": len(links_generated)
        })
    }
