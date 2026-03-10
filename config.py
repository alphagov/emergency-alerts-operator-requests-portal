import os


config = {
    # Retry / timing knobs
    "verify_code_retry_times": 5,
    "verify_code_retry_interval": 1,
    "dynamodb_query_retry_times": 20,
    "dynamodb_query_retry_interval": 3,
}

urls = {
    "development": {
        "portal": "https://operator-requests.dev.emergency-alerts.service.gov.uk",
    },
    "preview": {
        "portal": "https://operator-requests.preview.emergency-alerts.service.gov.uk",
    },
}


def setup_config():
    env = os.environ.get("ENVIRONMENT", "development").lower()

    if env not in {"development", "preview"}:
        raise ValueError(f'ENVIRONMENT "{env}" must be one of: development, preview')

    config.update(
        {
            "env": env,
            "portal_url": urls[env]["portal"],
            # AWS config for cross-account access
            "aws_region": os.environ.get("AWS_REGION", "eu-west-2"),
            "mno_portal_account_id": os.environ["MNO_PORTAL_ACCOUNT_ID"],
            # Log upload Lambda (invoked directly by the test to trigger the flow)
            "log_upload_lambda_name": os.environ["LOG_UPLOAD_LAMBDA_NAME"],
            # S3 bucket where uploaded logs land
            "log_bucket_name": os.environ["LOG_BUCKET_NAME"],
            # Notify API key — used to poll received emails via the Notify API
            "notify_api_key": os.environ["NOTIFY_SERVICE_API_KEY"],
            # The dummy MNO used in tests — must exist as a configured MNO in the environment
            "test_mno": {
                "mno_id": os.environ["TEST_MNO_ID"],
                "email": os.environ["TEST_MNO_EMAIL"],
            },
            # DynamoDB tables
            "log_upload_tracking_table": os.environ.get(
                "LOG_UPLOAD_TRACKING_TABLE",
                "operator-request-portal-log-uploads",
            ),
            "log_invite_tracking_table": os.environ.get(
                "LOG_INVITE_TRACKING_TABLE",
                "operator-request-portal-log-invites",
            ),
        }
    )
