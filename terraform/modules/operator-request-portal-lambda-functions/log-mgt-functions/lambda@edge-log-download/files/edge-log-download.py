import os
import base64
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TRACK_TABLE = "operator-request-portal-download-tracking"

ddb = boto3.client(
    "dynamodb",
    region_name=os.environ.get("DYNAMODB_REGION", "eu-west-2")
)


def error_response(status_code: int, status_desc: str, body: str, error_type: str = None) -> dict:
    headers = {
        "cache-control": [{"key": "Cache-Control", "value": "no-cache"}],
        "content-type": [{"key": "Content-Type", "value": "text/plain; charset=utf-8"}]
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


def _pad(b64: str) -> str:
    return b64 + "=" * (4 - len(b64) % 4) if len(b64) % 4 else b64


def _mask_reference(reference: str) -> str:
    """Log-safe form of a reference: keeps the alert prefix, masks the high-entropy token suffix."""
    alert, sep, token_id = reference.rpartition("-")
    if not sep:
        return "***"
    return f"{alert}-***"


def _decode_token(token: str):
    raw_b64 = _pad(token)
    try:
        decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8")
        return raw_b64, decoded, None
    except Exception:
        pass

    raw_b64 = _pad(unquote(token))
    try:
        decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8")
        return raw_b64, decoded, None
    except Exception as e:
        logger.error("Failed to decode token: %s", e)
        return None, None, error_response(400, "Bad Request", "Invalid data token", "invalid_token")


def _parse_token(decoded: str):
    try:
        kv = dict(pair.split("=", 1) for pair in decoded.split("&"))
    except Exception as e:
        logger.error("Failed to parse token parameters: %s", e)
        return None, error_response(400, "Bad Request", "Malformed token parameters", "malformed_token")

    for field in ("alert", "mno", "expiry", "reference"):
        if field not in kv:
            logger.error("Missing required field: %s", field)
            return None, error_response(400, "Bad Request", f"Missing {field}", "missing_parameter")

    return kv, None


def _check_expiry(kv: dict):
    try:
        exp = datetime.strptime(kv["expiry"], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.error("Invalid expiry format: %s", e)
        return error_response(400, "Bad Request", "Invalid expiry format", "invalid_expiry")

    if datetime.now(timezone.utc) > exp:
        logger.warning("Expired token for reference: %s", _mask_reference(kv["reference"]))
        return error_response(403, "Forbidden", "This download link has expired", "expired_link")

    return None


def _get_tracking_record(reference: str, raw_b64: str):
    try:
        resp = ddb.get_item(TableName=TRACK_TABLE, Key={"RequestId": {"S": reference}})
    except Exception as e:
        logger.error("DynamoDB get_item failed for %s: %s", _mask_reference(reference), e)
        return None, error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    item = resp.get("Item")
    if not item:
        logger.warning("No tracking record found for reference: %s", _mask_reference(reference))
        return None, error_response(403, "Forbidden", "Invalid reference", "invalid_token")

    stored_token = item.get("RawDownloadToken", {}).get("S")
    if stored_token is None or stored_token != raw_b64:
        logger.warning("Token mismatch for reference: %s", _mask_reference(reference))
        return None, error_response(403, "Forbidden", "Invalid token", "invalid_token")

    return item, None


def _increment_download(reference: str):
    update_expr = (
        "SET DownloadCount = if_not_exists(DownloadCount, :zero) + :one,"
        " LastDownloadAt = :now, #u = :true"
    )
    try:
        ddb.update_item(
            TableName=TRACK_TABLE,
            Key={"RequestId": {"S": reference}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={"#u": "Used"},
            ExpressionAttributeValues={
                ":zero": {"N": "0"},
                ":one": {"N": "1"},
                ":true": {"BOOL": True},
                ":now": {"S": datetime.now(timezone.utc).isoformat()}
            }
        )
        return None
    except Exception as e:
        logger.error("Failed to update download count for %s: %s", _mask_reference(reference), e)
        return error_response(500, "Internal Server Error", "Could not track download")


def lambda_handler(event, context):
    req = event["Records"][0]["cf"]["request"]

    if req.get("method") != "GET":
        logger.warning("Invalid method: %s", req.get("method"))
        return error_response(403, "Forbidden", "Only GET is allowed", "method_not_allowed")

    qs = req.get("querystring", "")
    if not qs:
        return error_response(400, "Bad Request", "Missing query string", "missing_querystring")

    token = parse_qs(qs).get("data", [None])[0]
    if not token:
        return error_response(400, "Bad Request", "Missing data parameter", "missing_token")

    raw_b64, decoded, err = _decode_token(token)
    if err:
        return err

    kv, err = _parse_token(decoded)
    if err:
        return err

    err = _check_expiry(kv)
    if err:
        return err

    reference = kv["reference"]

    item, err = _get_tracking_record(reference, raw_b64)
    if err:
        return err

    err = _increment_download(reference)
    if err:
        return err

    download_count = int(item.get("DownloadCount", {}).get("N", "0")) + 1
    alert = kv["alert"]
    mno = kv["mno"]
    s3_path = f"/received/logs/{alert}/CBC_{alert}_{mno}.zip"
    req["uri"] = s3_path

    logger.info(
        "Download authorized: alert=%s mno=%s count=%d", alert, mno, download_count
    )
    return req
