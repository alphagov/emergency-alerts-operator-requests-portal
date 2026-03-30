"""
Functional test (1): Confirm initial log upload request flow works.

Steps:
  1. Invoke the log-upload-handler Lambda with a unique alert reference and
     the dummy test MNO details.
  2. Assert the Lambda returns a success response indicating invites were sent.
  3. Assert the invite tracking record was written to DynamoDB.
  4. Poll the Notify API and assert the invite email was delivered to the
     dummy MNO email address with the expected content (upload site link present).
"""

import logging
import re

from config import config
from tests.aws_utils import (
    get_invite_tracking_record,
    invoke_log_upload_lambda,
    poll_notify_for_email,
)

logger = logging.getLogger(__name__)


def test_log_upload_request_flow(
    test_alert_reference,
    safe_alert,
    mno_id,
    mno_email,
    upload_url_store,
):
    """
    Trigger the log upload invite flow and confirm:
    - The Lambda invocation succeeds and reports 1 link generated.
    - The invite tracking record is present in DynamoDB.
    - The invite email is delivered to the dummy MNO address via Notify.
    - The email contains a recognisable upload link pointing at the portal.
    """

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

    logger.info(
        "Step 3: polling Notify for invite email to %s", mno_email
    )

    # The Notify template subject will contain the alert reference / "upload"
    portal_host = config["portal_url"].removeprefix("https://")
    notification = poll_notify_for_email(
        mno_email=mno_email,
        expected_subject_fragment="CBC activity logs",
        retries=config["verify_code_retry_times"] * 4,
        interval=config["verify_code_retry_interval"] * 3,
    )

    logger.info("Step 3 PASSED: invite email delivered (notification id: %s)", notification["id"])

    logger.info("Step 4: asserting email contains a valid upload link")

    email_body = notification.get("body", "")

    # The Lambda embeds oneTimeLink: https://{portal}/received/logs/{safe_alert}/CBC_...zip?data=...
    assert portal_host in email_body, (
        f"Expected portal hostname '{portal_host}' in email body, got:\n{email_body}"
    )

    expected_path_fragment = f"/received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
    assert expected_path_fragment in email_body, (
        f"Expected upload path fragment '{expected_path_fragment}' in email body"
    )

    # Extract the full one-time upload URL and stash it for tests (2) and (3)
    pattern = re.compile(
        r"(https://" + re.escape(portal_host) + r"/received/logs/"
        + re.escape(safe_alert) + r"/CBC_" + re.escape(safe_alert)
        + r"_" + re.escape(mno_id) + r"\.zip\?data=[^\s]+)"
    )
    match = pattern.search(email_body)
    assert match, (
        "Could not extract upload URL from email body — pattern not matched"
    )

    upload_url = match.group(1).strip()
    upload_url_store["url"] = upload_url
    logger.info("Step 4 PASSED: upload URL extracted and stored: %s", upload_url)
