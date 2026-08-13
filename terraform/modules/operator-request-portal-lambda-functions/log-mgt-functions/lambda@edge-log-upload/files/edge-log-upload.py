import os
import re
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

S3_KEY_RE = re.compile(
    r"^/received/logs/(?P<broadcast>[^/]+)/CBC_[^_]+_[^_]+_(?P=broadcast)\.zip$"
)

MNO_ID_HEADER_NAME = "x-upload-token"


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


def _validate_request(mno_id: str, broadcast_id: str):
    """Returns (item, error_response) — exactly one of the pair will be None."""
    if not mno_id:
        return None, error_response(400, "Bad Request", "Missing mno parameter", "missing_mno")
    if not broadcast_id:
        return None, error_response(400, "Bad Request", "Missing broadcast_id parameter", "missing_broadcast_id")

    composite_key = f"{mno_id}#{broadcast_id}"

    item, err = _get_tracking_record(composite_key)
    if err:
        return None, err
    if not item:
        logger.warning("No tracking record for mno=%s broadcast_id=%s", mno_id, broadcast_id)
        return None, error_response(403, "Forbidden", "Invalid mno or broadcast_id", "invalid_request")

    err = _check_expiry(item)
    if err:
        return None, err

    if item.get("Used", {}).get("BOOL", False):
        return None, error_response(403, "Forbidden", "This link has already been used", "already_used")

    return item, None


def _handle_viewer_request(req):
    logger.info("Lambda@Edge invoked: method=%s uri=%s", req.get("method"), req.get("uri"))

    if req.get("method") != "PUT":
        return error_response(403, "Forbidden", "Only PUT is allowed", "method_not_allowed")

    mno_id, broadcast_id = _parse_params(req.get("querystring", ""))
    item, err = _validate_request(mno_id, broadcast_id)
    if err:
        return err

    s3_location = item.get("S3Location", {}).get("S")
    if not s3_location:
        logger.error("No S3Location in tracking record for %s#%s", mno_id, broadcast_id)
        return error_response(500, "Internal Server Error", "Missing upload destination", "internal_error")

    req["uri"] = s3_location
    req["querystring"] = ""
    req.setdefault("headers", {})[MNO_ID_HEADER_NAME] = [
        {"key": "X-Upload-Token", "value": mno_id}
    ]
    logger.info(
        "Upload validated, forwarding to origin: uri=%s (mno=%s, broadcast_id=%s)",
        req["uri"], mno_id, broadcast_id
    )
    return req


def _handle_origin_response(request, response):
    status = response.get("status", "")
    match = S3_KEY_RE.match(request.get("uri", ""))
    if not match:
        return response
    broadcast_id = match.group("broadcast")

    mno_id_header = request.get("headers", {}).get(MNO_ID_HEADER_NAME)
    mno_id = mno_id_header[0].get("value") if mno_id_header else None
    if not mno_id:
        return response

    composite_key = f"{mno_id}#{broadcast_id}"

    if not status.startswith("2"):
        logger.warning(
            "Origin write failed (status=%s) for mno=%s broadcast_id=%s; upload link left unused for retry",
            status, mno_id, broadcast_id
        )
        return response

    err = _mark_used(composite_key)
    if err:
        logger.error("Failed to mark upload link used after successful write for %s", composite_key)
    else:
        logger.info("Upload confirmed, link marked used: mno=%s broadcast_id=%s", mno_id, broadcast_id)
    return response


def lambda_handler(event, context):
    cf = event["Records"][0]["cf"]
    event_type = cf["config"]["eventType"]

    if event_type == "viewer-request":
        return _handle_viewer_request(cf["request"])

    if event_type == "origin-response":
        return _handle_origin_response(cf["request"], cf["response"])

    logger.warning("Unhandled event type: %s", event_type)
    return cf.get("response") or cf["request"]
