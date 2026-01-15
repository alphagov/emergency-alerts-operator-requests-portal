import os
import re
import base64
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TRACK_TABLE = "dev-log-upload-tracking"

ddb = boto3.client(
    "dynamodb",
    region_name=os.environ.get("DYNAMODB_REGION", "eu-west-2")
)


def error_response(status_code: int, status_desc: str, body: str, error_type: str = None) -> dict:
    headers = {
        "cache-control": [{
            "key": "Cache-Control",
            "value": "no-cache"
        }],
        "content-type": [{
            "key": "Content-Type",
            "value": "text/html; charset=utf-8"
        }]
    }
    if error_type:
        headers["x-error-type"] = [{
            "key": "X-Error-Type",
            "value": error_type
        }]
    return {
        "status": str(status_code),
        "statusDescription": status_desc,
        "body": body,
        "bodyEncoding": "text",
        "headers": headers
    }


def lambda_handler(event, context):
    logger.info("Lambda@Edge invoked. Event: %s", event)
    req = event["Records"][0]["cf"]["request"]

    if req.get("method") != "PUT":
        return error_response(403, "Forbidden", "Only PUT is allowed", "method_not_allowed")

    qs = req.get("querystring", "")
    if not qs:
        return error_response(400, "Bad Request", "Missing query string", "missing_querystring")

    token = parse_qs(qs).get("data", [None])[0]
    if not token:
        return error_response(400, "Bad Request", "Missing data parameter", "missing_token")

    raw_b64 = token
    if len(raw_b64) % 4:
        raw_b64 += "=" * (4 - len(raw_b64) % 4)

    try:
        decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8")
        logger.info("Decoded token: %s", decoded)
    except Exception:
        return error_response(400, "Bad Request", "Invalid data token", "invalid_token")

    try:
        kv = dict(pair.split("=", 1) for pair in decoded.split("&"))
    except Exception:
        return error_response(400, "Bad Request", "Malformed token parameters", "malformed_token")

    for f in ("location", "type", "expiry", "reference"):
        if f not in kv:
            return error_response(400, "Bad Request", f"Missing {f}", "missing_parameter")
    if kv["type"] != "upload":
        return error_response(400, "Bad Request", "Invalid request type", "invalid_type")

    try:
        exp = datetime.strptime(kv["expiry"], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    except Exception:
        return error_response(400, "Bad Request", "Invalid expiry format", "invalid_expiry")
    if datetime.now(timezone.utc) > exp:
        return error_response(403, "Forbidden", "This upload link has expired", "expired_link")

    reference = kv["reference"]

    try:
        resp = ddb.get_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": reference}}
        )
    except Exception as e:
        logger.error("DynamoDB get_item failed for %s: %s", reference, e)
        return error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    item = resp.get("Item")
    if not item:
        logger.warning("No tracking record for %s", reference)
        return error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    stored_token = item.get("RawToken", {}).get("S")
    if stored_token is None or stored_token != raw_b64:
        logger.warning("Token mismatch: client sent %s, but DynamoDB has %s", raw_b64, stored_token)
        return error_response(400, "Forbidden", "Invalid token", "invalid_token")

    loc = kv["location"]
    m = re.match(
        r"^/received/logs/(?P<alert>[\w-]+)/CBC_(?P=alert)_(?P<mno>[^.]+)\.zip$",
        loc
    )
    if not m:
        return error_response(400, "Bad Request", "Invalid upload location", "invalid_location")

    if item.get("Used", {}).get("BOOL", False):
        return error_response(403, "Forbidden", "This link has already been used", "already_used")

    try:
        ddb.update_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": reference}},
            UpdateExpression="SET #u = :true, UsedAt = :now",
            ConditionExpression="attribute_not_exists(#u) OR #u = :false",
            ExpressionAttributeNames={"#u": "Used"},
            ExpressionAttributeValues={
                ":true": {"BOOL": True},
                ":false": {"BOOL": False},
                ":now": {"S": datetime.now(timezone.utc).isoformat()}
            }
        )
    except ddb.exceptions.ConditionalCheckFailedException:
        return error_response(403, "Forbidden", "This link has already been used", "already_used")
    except Exception as e:
        logger.error("DynamoDB error in mark_used: %s", e)
        return error_response(403, "Forbidden", "This link has already been used", "already_used")

    req["uri"] = loc
    req["querystring"] = ""
    logger.info("Upload allowed: %s (ref=%s)", req["uri"], reference)
    return req
