import json
import boto3
import logging
import os
from notifications_python_client.notifications import NotificationsAPIClient

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SSM client
ssm = boto3.client('ssm')

NOTIFY_PARAM_NAME = os.environ.get("NOTIFY_API_KEY_PARAM")


def get_notify_api_key():
    """Retrieve the GOV.UK Notify API key from Parameter Store"""
    try:
        response = ssm.get_parameter(
            Name=NOTIFY_PARAM_NAME,
            WithDecryption=True
        )
        return response["Parameter"]["Value"].strip()
    except Exception as e:
        logger.error(f"Error retrieving API key from Parameter Store: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    This is a 'middleman' function for sending emails via GOV.UK Notify.
    It accepts a payload with the following structure:
    {
        "email_address": "mno@example.com",
        "template_id": "template-id-guid",
        "personalisation": {
            --- personalisation key/values ---
        }
    }
    It acts as a 'middleman' by forwarding this payload to Notify and returning a response.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Validate required fields
        required_fields = ["email_address", "template_id", "personalisation"]
        missing_fields = [field for field in required_fields if field not in event]

        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_message)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_message})
            }

        # Initialize the Notify client for each invocation
        notify_client = NotificationsAPIClient(get_notify_api_key())

        # Send the notification
        response = notify_client.send_email_notification(
            email_address=event["email_address"],
            template_id=event["template_id"],
            personalisation=event["personalisation"]
        )

        logger.info(f"Notification sent successfully. ID: {response.get('id')}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Notify email sent successfully.",
                "notification_id": response.get("id")
            })
        }

    except ValueError as e:
        # Handle JSON parsing errors or validation errors
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        # Handle all other errors
        logger.error(f"Error sending Notify email: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
