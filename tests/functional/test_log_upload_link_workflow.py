"""
Rather than individual tests - this is an amalgamation of the workflow inside of one test to keep it ATOMIC
  1. Invoke the log-upload-handler Lambda and confirm the invite is created.
  2. Verify the invite tracking record in DynamoDB (composite key mno_id#broadcast_id).
  3. Poll Notify for the invite email and extract the upload URL.
  4. PUT a dummy .zip to the upload URL and confirm HTTP 200 + S3 object exists.
  5. PUT again to the same URL and confirm HTTP 403 (single-use link enforced).
"""

import io
import logging
import re
import uuid
import zipfile

import pytest
import requests

from config import config
from tests.aws_utils import (
    delete_invite_tracking_record,
    delete_s3_object,
    get_invite_tracking_record,
    invoke_log_upload_lambda,
    poll_notify_for_email,
    s3_object_exists,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def broadcast_id():
    bid = str(uuid.uuid4())
    logger.info("Test session broadcast_id: %s", bid)
    return bid


@pytest.fixture(scope="session")
def mno_id():
    return config["test_mno"]["mno_id"]


@pytest.fixture(scope="session")
def mno_portal_id():
    return config["test_mno"]["portal_id"]


@pytest.fixture(scope="session")
def mno_email():
    return config["test_mno"]["email"]


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(broadcast_id, mno_portal_id):
    yield

    logger.info("=== Teardown: cleaning up test artefacts for broadcast %s ===", broadcast_id)

    try:
        delete_invite_tracking_record(mno_portal_id, broadcast_id)
    except Exception as e:
        logger.warning("Could not delete invite tracking record: %s", e)

    s3_key = f"received/logs/{broadcast_id}/CBC_{broadcast_id}_{mno_portal_id}.zip"
    try:
        delete_s3_object(s3_key)
    except Exception as e:
        logger.warning("Could not delete S3 object %s: %s", s3_key, e)


def _make_dummy_zip(content: str = "MNO portal functional test log content") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.log", content)
    return buf.getvalue()


def test_log_upload_end_to_end(
    broadcast_id,
    mno_id,
    mno_portal_id,
    mno_email,
):
    alert_reference = f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}"
    logger.info("Step 1: invoking log-upload Lambda for broadcast_id '%s'", broadcast_id)

    response = invoke_log_upload_lambda(
        alert_reference=alert_reference,
        mno_id=mno_id,
        broadcast_id=broadcast_id,
    )

    assert response.get("statusCode") == 200, (
        f"Lambda returned unexpected statusCode: {response}"
    )

    body = response.get("body", {})
    assert body.get("links_generated") == 1, (
        f"Expected 1 upload link to be generated, got: {body}"
    )

    logger.info("Step 1 PASSED: Lambda invocation succeeded, 1 link generated")

    logger.info("Step 2: checking invite tracking record in DynamoDB")

    invite_record = get_invite_tracking_record(mno_portal_id, broadcast_id)
    assert invite_record is not None, (
        f"No invite tracking record found for portal_id '{mno_portal_id}' broadcast '{broadcast_id}' "
        f"in table '{config['log_invite_tracking_table']}'"
    )
    expected_key = f"{mno_portal_id}#{broadcast_id}"
    assert invite_record.get("AlertRef", {}).get("S") == expected_key

    logger.info("Step 2 PASSED: invite tracking record present in DynamoDB")

    logger.info("Step 3: polling Notify for invite email to %s", mno_email)

    portal_host = config["portal_url"].removeprefix("https://")
    notification = poll_notify_for_email(
        mno_email=mno_email,
        expected_subject_fragment="CBC activity logs",
        alert_reference=broadcast_id,
        retries=config["verify_code_retry_times"] * 4,
        interval=config["verify_code_retry_interval"] * 3,
    )

    logger.info("Step 3 PASSED: invite email delivered (notification id: %s)", notification["id"])

    email_body = notification.get("body", "")

    assert portal_host in email_body, (
        f"Expected portal hostname '{portal_host}' in email body, got:\n{email_body}"
    )

    pattern = re.compile(
        r"(https://" + re.escape(portal_host)
        + r"/log-upload\?mno=" + re.escape(mno_portal_id)
        + r"&broadcast_id=" + re.escape(broadcast_id) + r")"
    )
    match = pattern.search(email_body)
    assert match, "Could not extract upload URL from email body — pattern not matched"

    upload_url = match.group(1).strip()
    logger.info("Step 3 URL extraction PASSED: %s", upload_url)

    logger.info("Step 4: uploading dummy .zip via PUT")

    dummy_zip = _make_dummy_zip()
    put_response = requests.put(
        upload_url,
        data=dummy_zip,
        headers={"Content-Type": "application/zip"},
        timeout=30,
    )

    logger.info(
        "PUT response: HTTP %s — %s", put_response.status_code, put_response.text[:200]
    )

    assert put_response.status_code == 200, (
        f"Expected HTTP 200 from the upload endpoint, got {put_response.status_code}. "
        f"Response body: {put_response.text[:500]}"
    )

    expected_key = f"received/logs/{broadcast_id}/CBC_{broadcast_id}_{mno_portal_id}.zip"
    assert s3_object_exists(expected_key), (
        f"Expected S3 object not found: s3://{config['log_bucket_name']}/{expected_key}"
    )

    logger.info("Step 4 PASSED: upload succeeded, object confirmed in S3")

    logger.info("Step 5: attempting second upload to confirm single-use enforcement")

    replay_zip = _make_dummy_zip("second attempt — should be rejected")
    replay_response = requests.put(
        upload_url,
        data=replay_zip,
        headers={"Content-Type": "application/zip"},
        timeout=30,
    )

    logger.info(
        "Replay PUT response: HTTP %s — %s",
        replay_response.status_code,
        replay_response.text[:200],
    )

    assert replay_response.status_code == 403, (
        f"Expected HTTP 403 (link already used), got {replay_response.status_code}. "
        f"Response body: {replay_response.text[:500]}"
    )

    error_type = replay_response.headers.get("X-Error-Type", "")
    assert error_type == "already_used", (
        f"Expected X-Error-Type header 'already_used', got '{error_type}'"
    )

    assert "already been used" in replay_response.text.lower(), (
        f"Expected response body to mention 'already been used', got: {replay_response.text[:300]}"
    )

    logger.info("Step 5 PASSED: portal correctly refused second upload with HTTP 403")
