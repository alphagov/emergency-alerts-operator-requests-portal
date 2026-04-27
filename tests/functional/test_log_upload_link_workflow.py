"""
Functional test: end-to-end log upload flow.

Covers the full lifecycle:
  1. Invoke the log-upload-handler Lambda and confirm the invite is created.
  2. Verify the invite tracking record in DynamoDB.
  3. Poll Notify for the invite email and extract the one-time upload URL.
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


def _make_dummy_zip(content: str = "MNO portal functional test log content") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.log", content)
    return buf.getvalue()


def test_log_upload_end_to_end(
    test_alert_reference,
    safe_alert,
    mno_id,
    mno_email,
):
    logger.info("Step 1: invoking log-upload Lambda for alert '%s'", test_alert_reference)

    response = invoke_log_upload_lambda(
        alert_reference=test_alert_reference,
        mno_id=mno_id,
        mno_email=mno_email,
    )

    assert response.get("statusCode") == 200, (
        f"Lambda returned unexpected statusCode: {response}"
    )

    body = response.get("body", {})
    assert body.get("links_generated") == 1, (
        f"Expected 1 upload link to be generated, got: {body}"
    )
    assert body.get("alert_reference") == test_alert_reference, (
        f"Lambda echoed unexpected alert_reference: {body}"
    )

    logger.info("Step 1 PASSED: Lambda invocation succeeded, 1 link generated")

    logger.info("Step 2: checking invite tracking record in DynamoDB")

    invite_record = get_invite_tracking_record(test_alert_reference)
    assert invite_record is not None, (
        f"No invite tracking record found for alert '{test_alert_reference}' "
        f"in table '{config['log_invite_tracking_table']}'"
    )
    assert invite_record.get("AlertRef", {}).get("S") == test_alert_reference

    logger.info("Step 2 PASSED: invite tracking record present in DynamoDB")

    logger.info("Step 3: polling Notify for invite email to %s", mno_email)

    portal_host = config["portal_url"].removeprefix("https://")
    notification = poll_notify_for_email(
        mno_email=mno_email,
        expected_subject_fragment="CBC activity logs",
        alert_reference=test_alert_reference,
        retries=config["verify_code_retry_times"] * 4,
        interval=config["verify_code_retry_interval"] * 3,
    )

    logger.info("Step 3 PASSED: invite email delivered (notification id: %s)", notification["id"])

    email_body = notification.get("body", "")

    assert portal_host in email_body, (
        f"Expected portal hostname '{portal_host}' in email body, got:\n{email_body}"
    )

    expected_path_fragment = f"/received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
    assert expected_path_fragment in email_body, (
        f"Expected upload path fragment '{expected_path_fragment}' in email body"
    )

    pattern = re.compile(
        r"(https://" + re.escape(portal_host) + r"/received/logs/"
        + re.escape(safe_alert) + r"/CBC_" + re.escape(safe_alert)
        + r"_" + re.escape(mno_id) + r"\.zip\?data=[^\s]+)"
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

    expected_key = f"received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
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
