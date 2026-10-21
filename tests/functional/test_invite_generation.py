import logging
import re
import uuid
from datetime import datetime, timedelta

from config import config
from tests.aws_utils import (
    wait_for_cloudwatch_logs,
    get_invite_tracking_record,
    get_upload_tracking_record,
    invoke_log_upload_lambda,
)

logger = logging.getLogger(__name__)


def test_invite_happy_path(broadcast_id, mno_id, mno_label):
    response = invoke_log_upload_lambda(
        alert_reference=f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}",
        mno_id=mno_id,
        broadcast_id=broadcast_id,
    )
    assert response.get("statusCode") == 200
    assert response.get("body", {}).get("links_generated") == 1

    invite_record = get_invite_tracking_record(mno_label, broadcast_id)
    assert invite_record is not None
    assert invite_record["AlertRef"]["S"] == f"{mno_label}#{broadcast_id}"


def test_duplicate_invite_is_idempotent(broadcast_id, mno_id, mno_label):
    alert_reference = f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}"

    first = invoke_log_upload_lambda(alert_reference, mno_id, broadcast_id)
    assert first.get("body", {}).get("links_generated") == 1

    first_record = get_invite_tracking_record(mno_label, broadcast_id)
    first_invited_at = first_record["InvitedAt"]["S"]

    second = invoke_log_upload_lambda(alert_reference, mno_id, broadcast_id)
    assert second.get("statusCode") == 200
    assert second.get("body", {}).get("links_generated") == 0, (
        "Duplicate invite should be skipped, not generate a second link"
    )

    second_record = get_invite_tracking_record(mno_label, broadcast_id)
    assert second_record["InvitedAt"]["S"] == first_invited_at, (
        "Invite tracking record should be untouched by the duplicate call"
    )


def test_invite_for_unknown_mno_does_not_crash(broadcast_id, mno_label):
    "An mno_id with no SSM email/portal-id entry fails gracefully."
    unknown_mno_id = f"unknown-mno-{uuid.uuid4().hex[:8]}"

    response = invoke_log_upload_lambda(
        alert_reference=f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}",
        mno_id=unknown_mno_id,
        broadcast_id=broadcast_id,
    )
    assert response.get("statusCode") == 200, "Unknown MNO should not crash the Lambda"
    assert response.get("body", {}).get("links_generated") == 0

    assert get_invite_tracking_record(unknown_mno_id.upper(), broadcast_id) is None, (
        "No invite tracking record should be written for an unresolvable MNO"
    )


def test_invite_link_expiry_window(broadcast_id, mno_id, mno_portal_id):
    "ExpiresAt matches UPLOAD_LINK_EXPIRY_SECONDS (default 7 days) from now."
    invoke_log_upload_lambda(
        alert_reference=f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}",
        mno_id=mno_id,
        broadcast_id=broadcast_id,
    )

    record = get_upload_tracking_record(mno_portal_id, broadcast_id)
    assert record is not None

    expires_at = datetime.fromisoformat(record["ExpiresAt"]["S"])
    created_at = datetime.fromisoformat(record["CreatedAt"]["S"])
    delta = expires_at - created_at
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1), (
        f"Expected ~7 day expiry window, got {delta}"
    )


def test_invite_pii_masked_in_logs(broadcast_id, mno_id, mno_email):
    "Email addresses never appear unmasked in log-upload-handler logs."
    invoke_log_upload_lambda(
        alert_reference=f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}",
        mno_id=mno_id,
        broadcast_id=broadcast_id,
    )

    matches = wait_for_cloudwatch_logs(
        config["log_upload_lambda_name"],
        filter_pattern=f'"{broadcast_id}"',
    )
    assert matches, f"No log lines found for broadcast {broadcast_id} — check the log group name/timing"
    full_email_pattern = re.compile(re.escape(mno_email))
    leaked = [line for line in matches if full_email_pattern.search(line)]
    assert not leaked, f"Full email address found unmasked in logs: {leaked}"
