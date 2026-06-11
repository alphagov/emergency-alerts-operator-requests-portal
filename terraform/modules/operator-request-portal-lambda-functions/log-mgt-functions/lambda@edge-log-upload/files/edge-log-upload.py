import os
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TRACK_TABLE = "operator-request-portal-log-uploads"

ddb = boto3.client(
    "dynamodb",
    region_name=os.environ.get("DYNAMODB_REGION", "eu-west-2")
)


def error_response(status_code: int, status_desc: str, body: str, error_type: str = None) -> dict:
    headers = {
        "cache-control": [{"key": "Cache-Control", "value": "no-cache"}],
        "content-type": [{"key": "Content-Type", "value": "text/html; charset=utf-8"}]
    }
    if error_type:
        headers["x-error-type"] = [{"key": "X-Error-Type", "value": error_type}]
    return {
        "status": str(status_code),
        "statusDescription": status_desc,
        "body": body,
        "bodyEncoding": "text",
        "headers": headers
    }


def _parse_params(qs: str):
    params = parse_qs(qs)
    mno_id = params.get("mno", [None])[0]
    broadcast_id = params.get("broadcast_id", [None])[0]
    return mno_id, broadcast_id


def _get_tracking_record(composite_key: str):
    try:
        resp = ddb.get_item(TableName=TRACK_TABLE, Key={"RequestId": {"S": composite_key}})
        return resp.get("Item"), None
    except Exception as e:
        logger.error("DynamoDB get_item failed for %s: %s", composite_key, e)
        return None, error_response(403, "Forbidden", "Invalid request", "invalid_request")


def _check_expiry(item: dict):
    expires_at_str = item.get("ExpiresAt", {}).get("S")
    if not expires_at_str:
        return None
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return error_response(403, "Forbidden", "This upload link has expired", "expired_link")
    except Exception as e:
        logger.warning("Could not parse ExpiresAt '%s': %s", expires_at_str, e)
    return None


def _mark_used(composite_key: str):
    try:
        ddb.update_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": composite_key}},
            UpdateExpression="SET #u = :true, UsedAt = :now",
            ConditionExpression="attribute_not_exists(#u) OR #u = :false",
            ExpressionAttributeNames={"#u": "Used"},
            ExpressionAttributeValues={
                ":true": {"BOOL": True},
                ":false": {"BOOL": False},
                ":now": {"S": datetime.now(timezone.utc).isoformat()}
            }
        )
        return None
    except ddb.exceptions.ConditionalCheckFailedException:
        return error_response(403, "Forbidden", "This link has already been used", "already_used")
    except Exception as e:
        logger.error("DynamoDB error marking upload used for %s: %s", composite_key, e)
        return error_response(500, "Internal Server Error", "Processing error", "internal_error")


def lambda_handler(event, context):
    logger.info("Lambda@Edge invoked. Event: %s", event)
    req = event["Records"][0]["cf"]["request"]

    if req.get("method") != "PUT":
        return error_response(403, "Forbidden", "Only PUT is allowed", "method_not_allowed")

    mno_id, broadcast_id = _parse_params(req.get("querystring", ""))

    if not mno_id:
        return error_response(400, "Bad Request", "Missing mno parameter", "missing_mno")
    if not broadcast_id:
        return error_response(400, "Bad Request", "Missing broadcast_id parameter", "missing_broadcast_id")

    composite_key = f"{mno_id}#{broadcast_id}"

    item, err = _get_tracking_record(composite_key)
    if err:
        return err
    if not item:
        logger.warning("No tracking record for mno=%s broadcast_id=%s", mno_id, broadcast_id)
        return error_response(403, "Forbidden", "Invalid mno or broadcast_id", "invalid_request")

    err = _check_expiry(item)
    if err:
        return err

    if item.get("Used", {}).get("BOOL", False):
        return error_response(403, "Forbidden", "This link has already been used", "already_used")

    err = _mark_used(composite_key)
    if err:
        return err

    s3_location = item.get("S3Location", {}).get("S")
    if not s3_location:
        logger.error("No S3Location in tracking record for %s", composite_key)
        return error_response(500, "Internal Server Error", "Missing upload destination", "internal_error")

    req["uri"] = s3_location
    req["querystring"] = ""
    logger.info("Upload allowed: uri=%s (mno=%s, broadcast_id=%s)", req["uri"], mno_id, broadcast_id)
    return req
