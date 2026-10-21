import logging
import re
import uuid

import requests

from config import config
from tests.aws_utils import (
    get_invite_tracking_record,
    get_upload_tracking_record,
    invoke_log_upload_lambda,
    make_zip_bytes,
    poll_notify_for_email,
    s3_object_exists,
    wait_for_cloudwatch_logs,
)

logger = logging.getLogger(__name__)


def test_log_upload_end_to_end(broadcast_id, mno_id, mno_portal_id, mno_email, mno_label):
    alert_reference = f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}"
    logger.info("Step 1: invoking log-upload Lambda for broadcast_id '%s'", broadcast_id)

    response = invoke_log_upload_lambda(
        alert_reference=alert_reference, mno_id=mno_id, broadcast_id=broadcast_id
    )
    assert response.get("statusCode") == 200, f"Lambda returned unexpected statusCode: {response}"

    body = response.get("body", {})
    assert body.get("links_generated") == 1, f"Expected 1 upload link to be generated, got: {body}"

    invite_record = get_invite_tracking_record(mno_label, broadcast_id)
    assert invite_record is not None, (
        f"No invite tracking record found for mno_label '{mno_label}' broadcast '{broadcast_id}'"
    )

    logger.info("Step 2: polling Notify for invite email to %s", mno_email)
    portal_host = config["portal_url"].removeprefix("https://")
    notification = poll_notify_for_email(
        mno_email=mno_email,
        expected_subject_fragment="CBC activity logs",
        alert_reference=broadcast_id,
        retries=config["verify_code_retry_times"] * 4,
        interval=config["verify_code_retry_interval"] * 3,
    )
    email_body = notification.get("body", "")

    pattern = re.compile(
        r"https://" + re.escape(portal_host) + r"/upload-logs\.html\?broadcast_id=" + re.escape(broadcast_id)
    )
    assert pattern.search(email_body), f"Upload page link not found in email body:\n{email_body}"
    upload_url = f"{config['portal_url']}/log-upload?mno={mno_portal_id}&broadcast_id={broadcast_id}"

    logger.info("Step 3: uploading dummy .zip via PUT")
    put_response = requests.put(
        upload_url,
        data=make_zip_bytes(),
        headers={"Content-Type": "application/zip"},
        timeout=30,
    )
    assert put_response.status_code == 200, (
        f"Expected HTTP 200 from the upload endpoint, got {put_response.status_code}. "
        f"Response body: {put_response.text[:500]}"
    )

    logger.info("Step 4: confirming the real S3 key (from the tracking record, not assumed)")
    upload_record = get_upload_tracking_record(mno_portal_id, broadcast_id)
    assert upload_record is not None, "No upload tracking record found after successful upload"
    s3_key = upload_record["S3Location"]["S"].lstrip("/")
    logger.info("Actual uploaded S3 key: %s", s3_key)
    assert s3_object_exists(s3_key), f"Expected S3 object not found: s3://{config['log_bucket_name']}/{s3_key}"

    logger.info("Step 5: confirming internal notify notification fired for this key")
    matches = wait_for_cloudwatch_logs(
        config["log_download_lambda_name"],
        filter_pattern=f'"Sent download notification for {broadcast_id}"',
    )
    assert matches, (
        f"No 'Sent download notification' log line found for broadcast {broadcast_id} in "
        f"{config['log_download_lambda_name']} — internal notify may not have fired"
    )

    logger.info("Step 6: attempting second upload to confirm single-use enforcement")
    replay_response = requests.put(
        upload_url,
        data=make_zip_bytes("second attempt — should be rejected"),
        headers={"Content-Type": "application/zip"},
        timeout=30,
    )
    assert replay_response.status_code == 403, (
        f"Expected HTTP 403 (link already used), got {replay_response.status_code}. "
        f"Response body: {replay_response.text[:500]}"
    )
    assert replay_response.headers.get("X-Error-Type") == "already_used"
