import os
import base64
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote
import re

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TRACK_TABLE = "dev-log-download-tracking"

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
            "value": "text/plain; charset=utf-8"
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
    req = event["Records"][0]["cf"]["request"]

    if req.get("method") != "GET":
        logger.warning("Invalid method: %s", req.get("method"))
        return error_response(403, "Forbidden", "Only GET is allowed", "method_not_allowed")

    qs = req.get("querystring", "")
    if not qs:
        logger.error("Missing query string")
        return error_response(400, "Bad Request", "Missing query string", "missing_querystring")

    parsed_qs = parse_qs(qs)
    token = parsed_qs.get("data", [None])[0]

    if not token:
        logger.error("Missing data parameter")
        return error_response(400, "Bad Request", "Missing data parameter", "missing_token")

    # Try decoding token
    raw_b64 = token
    if len(raw_b64) % 4:
        raw_b64 += "=" * (4 - len(raw_b64) % 4)

    try:
        decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8")
    except Exception:
        raw_b64 = unquote(token)
        if len(raw_b64) % 4:
            raw_b64 += "=" * (4 - len(raw_b64) % 4)

        try:
            decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8")
        except Exception as e:
            logger.error("Failed to decode token: %s", str(e))
            return error_response(400, "Bad Request", "Invalid data token", "invalid_token")

    try:
        kv = dict(pair.split("=", 1) for pair in decoded.split("&"))
    except Exception as e:
        logger.error("Failed to parse token parameters: %s", str(e))
        return error_response(400, "Bad Request", "Malformed token parameters", "malformed_token")

    # Validate required fields
    required_fields = ("alert", "mno", "expiry", "reference")
    for field in required_fields:
        if field not in kv:
            logger.error("Missing required field: %s", field)
            return error_response(400, "Bad Request", f"Missing {field}", "missing_parameter")

    # Check expiry
    try:
        exp = datetime.strptime(kv["expiry"], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.error("Invalid expiry format: %s", str(e))
        return error_response(400, "Bad Request", "Invalid expiry format", "invalid_expiry")

    if datetime.now(timezone.utc) > exp:
        logger.warning("Expired token for reference: %s", kv["reference"])
        return error_response(403, "Forbidden", "This download link has expired", "expired_link")

    reference = kv["reference"]

    # Validate token against database
    try:
        resp = ddb.get_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": reference}}
        )
    except Exception as e:
        logger.error("DynamoDB get_item failed for reference %s: %s", reference, str(e))
        return error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    item = resp.get("Item")
    if not item:
        logger.warning("No tracking record found for reference: %s", reference)
        return error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    stored_token = item.get("RawDownloadToken", {}).get("S")
    if stored_token is None or stored_token != raw_b64:
        logger.warning("Token mismatch for reference: %s", reference)
        return error_response(403, "Forbidden", "Invalid token", "invalid_token")

    # Track download count (but don't restrict multiple downloads for logs)
    download_count = item.get("DownloadCount", {}).get("N", "0")
    logger.info("Download count for reference %s: %s", reference, download_count)

    # Increment download count
    try:
        ddb.update_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": reference}},
            UpdateExpression="SET DownloadCount = if_not_exists(DownloadCount, :zero) + :one, LastDownloadAt = :now, #u = :true",
            ExpressionAttributeNames={"#u": "Used"},
            ExpressionAttributeValues={
                ":zero": {"N": "0"},
                ":one": {"N": "1"},
                ":true": {"BOOL": True},
                ":now": {"S": datetime.now(timezone.utc).isoformat()}
            }
        )
        logger.info("Incremented download count for reference: %s", reference)
    except Exception as e:
        logger.error("Failed to update download count for reference %s: %s", reference, str(e))
        return error_response(500, "Internal Server Error", "Could not track download")

    # Generate S3 path and allow download
    alert = kv["alert"]
    mno = kv["mno"]
    safe_alert = re.sub(r'[^A-Za-z0-9]+', '_', alert).strip('_')
    s3_path = f"/received/logs/{safe_alert}/CBC_{safe_alert}_{mno}.zip"
    req["uri"] = s3_path

    new_count = int(download_count) + 1
    logger.info("Download authorized for reference: %s, path: %s (download #%d)", reference, s3_path, new_count)
    return req
