import uuid
import logging
import re

import pytest

from config import config
from tests.aws_utils import (
    delete_invite_tracking_record,
    delete_s3_object
    # delete_upload_tracking_record,
    # get_invite_tracking_record,
    # get_upload_tracking_record,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def test_alert_reference():
    ref = f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}"
    logger.info("Test session alert reference: %s", ref)
    return ref


@pytest.fixture(scope="session")
def safe_alert(test_alert_reference):
    return re.sub(r"[^A-Za-z0-9]+", "_", test_alert_reference).strip("_")


@pytest.fixture(scope="session")
def mno_id():
    return config["test_mno"]["mno_id"]


@pytest.fixture(scope="session")
def mno_email():
    return config["test_mno"]["email"]


@pytest.fixture(scope="session")
def upload_url_store():
    return {"url": None}


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(test_alert_reference, safe_alert, mno_id):
    yield

    logger.info("=== Teardown: cleaning up test artefacts for %s ===", test_alert_reference)

    try:
        delete_invite_tracking_record(test_alert_reference)
    except Exception as e:
        logger.warning("Could not delete invite tracking record: %s", e)

    s3_key = f"received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
    try:
        delete_s3_object(s3_key)
    except Exception as e:
        logger.warning("Could not delete S3 object %s: %s", s3_key, e)
