import logging
import uuid

import pytest

from config import config
from tests.aws_utils import (
    delete_invite_tracking_record,
    delete_s3_prefix,
    delete_upload_tracking_record,
)
from tests.unit._lambda_loader import load_lambda_module

logger = logging.getLogger(__name__)

UPLOAD_HANDLER_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda-log-upload/files/log-upload-handler.py"
)

UPLOAD_HANDLER_ENV = {
    "LOG_BUCKET_NAME": "unused",
    "UPLOAD_DOMAIN": "unused",
    "NOTIFY_LAMBDA_ARN": "unused",
    "NOTIFY_LOG_TEMPLATE_ID": "unused",
    "LOG_INVITE_TRACKING_TABLE": "unused",
    "LOG_UPLOAD_TRACKING_TABLE": "unused",
}


@pytest.fixture
def broadcast_id():
    bid = str(uuid.uuid4())
    logger.info("Test broadcast_id: %s", bid)
    return bid


@pytest.fixture
def mno_id():
    return config["test_mno"]["mno_id"]


@pytest.fixture
def mno_portal_id():
    return config["test_mno"]["portal_id"]


@pytest.fixture
def mno_email():
    return config["test_mno"]["email"]


@pytest.fixture(scope="session")
def mno_label():
    handler = load_lambda_module(UPLOAD_HANDLER_PATH, "log_upload_handler_for_tests", UPLOAD_HANDLER_ENV)
    return handler._sanitize_for_filename(config["test_mno"]["mno_id"])


@pytest.fixture(autouse=True)
def cleanup_test_data(broadcast_id, mno_portal_id, mno_label):
    yield

    logger.info("=== Teardown: cleaning up test artefacts for broadcast %s ===", broadcast_id)

    for description, action in (
        ("invite tracking record", lambda: delete_invite_tracking_record(mno_label, broadcast_id)),
        ("upload tracking record", lambda: delete_upload_tracking_record(mno_portal_id, broadcast_id)),
        ("S3 objects", lambda: delete_s3_prefix(f"received/logs/{broadcast_id}/")),
    ):
        try:
            action()
        except Exception as e:
            logger.warning("Could not delete %s: %s", description, e)
