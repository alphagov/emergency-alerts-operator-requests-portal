import base64
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb', region_name='eu-west-2')


def error_response(message, status="400", statusDescription="Bad Request"):
    # Return an HTTP error response object
    return {
        "status": status,
        "statusDescription": statusDescription,
        "body": message,
        "headers": {
            "cache-control": [{
                "key": "Cache-Control",
                "value": "no-cache"
            }]
        }
    }


def verify_upload_request(request_id: str) -> dict:
    table_name = "csr-upload-tracking"
    current_time = datetime.utcnow().isoformat()
    try:
        response = dynamodb.update_item(
            TableName=table_name,
            Key={
                'RequestId': {'S': request_id}
            },
            UpdateExpression="SET #used = :true, #uploadTime = :time",
            ConditionExpression="attribute_not_exists(#used) OR #used = :false",
            ExpressionAttributeNames={
                "#used": "Used",
                "#uploadTime": "UploadTime"
            },
            ExpressionAttributeValues={
                ":true": {'BOOL': True},
                ":false": {'BOOL': False},
                ":time": {'S': current_time}
            },
            ReturnValues='ALL_NEW'
        )
        logger.info("Upload request verified and marked as used: %s", response)
        return {"valid": True, "data": response.get("Attributes")}
    except dynamodb.exceptions.ConditionalCheckFailedException:
        logger.error("Upload already processed: %s", request_id)
        return {"valid": False, "reason": "already-used"}
    except Exception as e:
        logger.error("Error verifying upload request: %s", str(e))
        return {"valid": False, "reason": "invalid-request"}


def parse_params(param_string: str) -> dict:
    # Expected format: location=upload/MNO002/CERT002.csr&type=upload&expiry=202504231200&reference=MNO002-CERT002
    params = {}
    pairs = param_string.split('&')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key] = value
    return params


def lambda_handler(event, context):
    try:
        # Get the CloudFront request object.
        request = event["Records"][0]["cf"]["request"]
        query_string = request.get("querystring", "")
        if not query_string:
            logger.error("Missing query string")
            return error_response("Missing query string", status="400", statusDescription="Bad Request")

        # Extract the 'data' parameter from the query string.
        qs_params = parse_qs(query_string)
        encoded_data = qs_params.get("data", [None])[0]
        if not encoded_data:
            logger.error("Missing 'data' parameter in query string.")
            return error_response("Missing 'data' parameter", status="400", statusDescription="Bad Request")

        # URL-decode the value.
        decoded_data = unquote(encoded_data)
        # Add padding if necessary.
        missing_padding = len(decoded_data) % 4
        if missing_padding:
            decoded_data += "=" * (4 - missing_padding)

        try:
            decoded_bytes = base64.urlsafe_b64decode(decoded_data)
            decoded_params_str = decoded_bytes.decode("utf-8")
        except Exception as e:
            logger.error("Failed to decode query parameters: %s", str(e))
            return error_response("Failed to decode query parameters", status="400", statusDescription="Bad Request")

        # Parse parameters from the decoded string.
        params = parse_params(decoded_params_str)
        if not all(key in params for key in ("location", "type", "expiry")):
            logger.error("Missing required parameters: %s", params)
            return error_response("Missing required parameters", status="400", statusDescription="Bad Request")

        if params.get("type") != "upload":
            logger.error("Invalid request type: %s", params.get("type"))
            return error_response("Invalid request type", status="400", statusDescription="Bad Request")

        expiry_str = params.get("expiry")
        if expiry_str is None:
            logger.error("Expiry parameter missing.")
            return error_response("Expiry parameter missing", status="400", statusDescription="Bad Request")

        try:
            expiry_dt = datetime.strptime(expiry_str, "%Y%m%d%H%M")
            expiry_timestamp = int(expiry_dt.replace(tzinfo=timezone.utc).timestamp())
        except Exception as e:
            logger.error("Failed to parse expiry timestamp: %s", str(e))
            return error_response("Failed to parse expiry timestamp", status="400", statusDescription="Bad Request")

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        if current_timestamp > expiry_timestamp:
            logger.error("Link has expired")
            return error_response("Link has expired", status="400", statusDescription="Bad Request")

        # Verify the upload request via DynamoDB.
        verification = verify_upload_request(query_string)
        if not verification.get("valid"):
            logger.error("Upload verification failed: %s", verification.get("reason", ""))
            return error_response("Upload verification failed", status="400", statusDescription="Bad Request")

        # Rewrite the request URI.
        location_param = params.get("location")
        if location_param is None:
            logger.error("Location parameter missing")
            return error_response("Location parameter missing", status="400", statusDescription="Bad Request")
        request["uri"] = location_param

        logger.info("Upload request validated successfully, final URI: %s", request["uri"])
        return request

    except Exception as error:
        logger.error("Unexpected error: %s", str(error))
        return error_response("Unexpected server error", status="500", statusDescription="Internal Server Error")
