import json
import logging
import time

import boto3

from config import config

logger = logging.getLogger(__name__)


def invoke_log_upload_lambda(alert_reference: str, mno_id: str, mno_email: str) -> dict:
    """
    Synchronously invoke the log-upload-handler Lambda to trigger the upload
    invite flow for a single MNO.

    Returns the parsed Lambda response body on success, or raises on failure.
    """
    client = boto3.client("lambda", region_name=config["aws_region"])

    payload = {
        "alert_reference": alert_reference,
        "environment": config["env"],
        "broadcast_start": "2025-01-01T09:00:00Z",
        "broadcast_end": "2025-01-01T09:15:00Z",
        "mnos": [
            {
                "mno_id": mno_id,
                "emails": [mno_email],
            }
        ],
    }

    logger.info("Invoking log-upload Lambda: %s", config["log_upload_lambda_name"])
    response = client.invoke(
        FunctionName=config["log_upload_lambda_name"],
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    status_code = response["StatusCode"]
    raw_payload = response["Payload"].read().decode("utf-8")
    logger.info("Lambda response status: %s, payload: %s", status_code, raw_payload)

    if response.get("FunctionError"):
        raise RuntimeError(
            f"Lambda function error: {response['FunctionError']} — {raw_payload}"
        )

    if status_code != 200:
        raise RuntimeError(
            f"Unexpected Lambda status code {status_code}: {raw_payload}"
        )

    body = json.loads(raw_payload)
    if isinstance(body.get("body"), str):
        body["body"] = json.loads(body["body"])

    return body


def get_upload_tracking_record(reference: str) -> dict | None:
    client = boto3.client("dynamodb", region_name=config["aws_region"])
    resp = client.get_item(
        TableName=config["log_upload_tracking_table"],
        Key={"RequestId": {"S": reference}},
    )
    return resp.get("Item")


def get_invite_tracking_record(alert_ref: str) -> dict | None:
    client = boto3.client("dynamodb", region_name=config["aws_region"])
    resp = client.get_item(
        TableName=config["log_invite_tracking_table"],
        Key={"AlertRef": {"S": alert_ref}},
    )
    return resp.get("Item")


def delete_invite_tracking_record(alert_ref: str):
    client = boto3.client("dynamodb", region_name=config["aws_region"])
    client.delete_item(
        TableName=config["log_invite_tracking_table"],
        Key={"AlertRef": {"S": alert_ref}},
    )
    logger.info("Deleted invite tracking record for alert: %s", alert_ref)


def delete_upload_tracking_record(reference: str):
    client = boto3.client("dynamodb", region_name=config["aws_region"])
    client.delete_item(
        TableName=config["log_upload_tracking_table"],
        Key={"RequestId": {"S": reference}},
    )
    logger.info("Deleted upload tracking record: %s", reference)


def s3_object_exists(key: str) -> bool:
    client = boto3.client("s3", region_name=config["aws_region"])
    try:
        client.head_object(Bucket=config["log_bucket_name"], Key=key)
        return True
    except client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def delete_s3_object(key: str):
    client = boto3.client("s3", region_name=config["aws_region"])
    client.delete_object(Bucket=config["log_bucket_name"], Key=key)
    logger.info("Deleted S3 object: s3://%s/%s", config["log_bucket_name"], key)


def poll_notify_for_email(
    mno_email: str,
    expected_subject_fragment: str,
    alert_reference: str = "",
    retries: int = 20,
    interval: int = 3,
) -> dict:
    from notifications_python_client import NotificationsAPIClient

    client = NotificationsAPIClient(config["notify_api_key"])

    for attempt in range(1, retries + 1):
        logger.info(
            "Polling Notify for email to %s (attempt %d/%d)", mno_email, attempt, retries
        )
        notifications = client.get_all_notifications(
            template_type="email", status="delivered"
        )
        for notification in notifications.get("notifications", []):
            if notification.get("email_address") != mno_email:
                continue
            subject = notification.get("subject", "") or ""
            if expected_subject_fragment.lower() not in subject.lower():
                continue
            if alert_reference and alert_reference not in subject:
                continue
            logger.info("Found matching notification: %s", notification.get("id"))
            return notification

        if attempt < retries:
            time.sleep(interval)

    raise AssertionError(
        f"No email with subject containing '{expected_subject_fragment}' "
        f"for alert '{alert_reference}' "
        f"delivered to {mno_email} after {retries * interval}s"
    )
