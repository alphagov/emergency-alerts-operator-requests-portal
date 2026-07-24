import os
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOG_BUCKET = os.environ["LOG_BUCKET_NAME"]
UPLOAD_DOMAIN = os.environ["UPLOAD_DOMAIN"]
NOTIFY_LAMBDA_ARN = os.environ["NOTIFY_LAMBDA_ARN"]
NOTIFY_TEMPLATE_ID = os.environ["NOTIFY_LOG_TEMPLATE_ID"]
LOG_INVITE_TRACKING_TABLE = os.environ["LOG_INVITE_TRACKING_TABLE"]
LOG_UPLOAD_TRACKING_TABLE = os.environ["LOG_UPLOAD_TRACKING_TABLE"]
EXPIRY_SECONDS = int(os.environ.get("UPLOAD_LINK_EXPIRY_SECONDS", "604800"))
MNO_EMAIL_SSM_PREFIX = os.environ.get("MNO_EMAIL_SSM_PREFIX", "/operator-portal/mno-emails")
MNO_ID_SSM_PREFIX = os.environ.get("MNO_ID_SSM_PREFIX", "/operator-portal/mno-ids")

ddb = boto3.client("dynamodb")
ssm = boto3.client("ssm")


def _get_mno_identifier(mno_id: str) -> str | None:
    param_name = f"{MNO_ID_SSM_PREFIX}/{mno_id.lower()}"
    try:
        resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return resp["Parameter"]["Value"].strip()
    except ssm.exceptions.ParameterNotFound:
        logger.warning(f"No portal identifier SSM parameter found at {param_name}")
        return None
    except Exception as e:
        logger.error(f"Error fetching SSM parameter {param_name}: {e}")
        return None


def _get_mno_emails(mno_id: str) -> list[str]:
    param_name = f"{MNO_EMAIL_SSM_PREFIX}/{mno_id.lower()}"
    try:
        resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
        raw = resp["Parameter"]["Value"]
        return [e.strip() for e in raw.split(",") if e.strip()]
    except ssm.exceptions.ParameterNotFound:
        logger.warning(f"No SSM parameter found at {param_name}")
        return []
    except Exception as e:
        logger.error(f"Error fetching SSM parameter {param_name}: {e}")
        return []


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    masked_local = f"{local[0]}***" if local else "***"
    return f"{masked_local}@{domain}"


def _mask_token(token: str) -> str:
    return f"{token[:6]}..." if len(token) > 6 else "***"


def _invite_key(mno_id: str, broadcast_id: str) -> str:
    return f"{mno_id}#{broadcast_id}"


def already_invited(mno_id: str, broadcast_id: str) -> bool:
    resp = ddb.get_item(
        TableName=LOG_INVITE_TRACKING_TABLE,
        Key={"AlertRef": {"S": _invite_key(mno_id, broadcast_id)}}
    )
    return "Item" in resp


def mark_invited(mno_id: str, broadcast_id: str):
    ddb.put_item(
        TableName=LOG_INVITE_TRACKING_TABLE,
        Item={
            "AlertRef": {"S": _invite_key(mno_id, broadcast_id)},
            "InvitedAt": {"S": datetime.now(timezone.utc).isoformat()}
        }
    )


def generate_upload_token() -> str:
    """
    Unguessable identifier used as both the DynamoDB partition key
    and the sole upload-authorisation credential
    """
    return secrets.token_urlsafe(32)


def register_upload_reference(
    token: str, mno_id: str, broadcast_id: str, s3_location: str, mno_name: str
) -> bool:
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=EXPIRY_SECONDS)).isoformat()
    try:
        ddb.put_item(
            TableName=LOG_UPLOAD_TRACKING_TABLE,
            Item={
                "RequestId": {"S": token},
                "CreatedAt": {"S": datetime.now(timezone.utc).isoformat()},
                "ExpiresAt": {"S": expires_at},
                "Used": {"BOOL": False},
                "S3Location": {"S": s3_location},
                "MnoId": {"S": mno_id},
                "MnoName": {"S": mno_name},
                "BroadcastId": {"S": broadcast_id}
            },
            ConditionExpression="attribute_not_exists(RequestId)"
        )
        logger.info(f"Registered upload reference {_mask_token(token)} → {s3_location}")
        return True
    except ddb.exceptions.ConditionalCheckFailedException:
        logger.warning(f"Upload reference {_mask_token(token)} already exists")
        return False
    except Exception as e:
        logger.error(f"Error registering upload reference {_mask_token(token)}: {e}")
        return False


def prepare_folder(broadcast_id: str):
    try:
        s3 = boto3.client("s3")
        s3.put_object(Bucket=LOG_BUCKET, Key=f"received/logs/{broadcast_id}/")
        logger.info(f"Created S3 prefix: received/logs/{broadcast_id}/")
    except Exception as e:
        logger.error(f"Error creating S3 prefix for broadcast {broadcast_id}: {e}")


def send_invite(email: str, token: str, broadcast_id: str, mno_name: str, portal_id: str):
    upload_site = f"https://{UPLOAD_DOMAIN}/upload-logs.html?token={token}"
    portal_upload_help = f"https://{UPLOAD_DOMAIN}/automate-upload.html"

    payload = {
        "email_address": email,
        "template_id": NOTIFY_TEMPLATE_ID,
        "personalisation": {
            "broadcastRef": broadcast_id,
            "MNO": mno_name,
            "MNOid": portal_id,
            "uploadSite": upload_site,
            "portalUploadHelp": portal_upload_help,
        }
    }
    try:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8")
        )
        logger.info(
            f"Sent invite to {_mask_email(email)} for MNO {mno_name} ({portal_id}) broadcast {broadcast_id}"
        )
    except Exception as e:
        logger.error(f"Error sending invite to {_mask_email(email)}: {e}")


def lambda_handler(event, context):
    """
    Handler for sending log-upload invites. Expects event:
    {
      "alert_reference": "<broadcast_event_id UUID>",
      "environment":     "dev",
      "broadcast_start": "2025-05-12T09:00:00Z",
      "broadcast_end":   "2025-05-12T09:15:00Z",
      "mnos": [
        { "mno_id": "ee",       "provider_message_id": "<BroadcastProviderMessage UUID>" },
        { "mno_id": "vodafone", "provider_message_id": "<BroadcastProviderMessage UUID>" }
      ]
    }

    mno_id is the operator name key used to look up both the contact email and the
    6-character portal identifier from SSM; it never appears in the event payload.
    The upload URL sent to each MNO carries a high-entropy opaque token (the
    DynamoDB partition key) rather than the portal identifier or broadcast ID.
    """
    alert_ref = event["alert_reference"]
    logger.info(f"Processing upload invite event: alert_reference={alert_ref}, mno_count={len(event.get('mnos', []))}")

    invites_sent = []

    for mno in event.get("mnos", []):
        mno_id = mno["mno_id"]
        broadcast_id = mno["provider_message_id"]

        portal_id = _get_mno_identifier(mno_id)
        if not portal_id:
            logger.warning(f"No portal identifier found for MNO {mno_id}, skipping")
            continue

        if already_invited(portal_id, broadcast_id):
            logger.info(f"Invite for MNO {mno_id} ({portal_id}) broadcast {broadcast_id} already sent, skipping")
            continue

        emails = _get_mno_emails(mno_id)
        if not emails:
            logger.warning(f"No emails found for MNO {mno_id}, skipping")
            continue

        s3_location = f"/received/logs/{broadcast_id}/CBC_{broadcast_id}_{portal_id}.zip"
        prepare_folder(broadcast_id)
        token = generate_upload_token()
        register_upload_reference(token, portal_id, broadcast_id, s3_location, mno_id)

        for email in emails:
            send_invite(email, token, broadcast_id, mno_id, portal_id)

        mark_invited(portal_id, broadcast_id)
        invites_sent.append({"mno_id": mno_id, "portal_id": portal_id})

    logger.info(f"Sent {len(invites_sent)} upload invite(s) for alert {alert_ref}")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Log upload invites sent",
            "alert_reference": alert_ref,
            "links_generated": len(invites_sent)
        })
    }
