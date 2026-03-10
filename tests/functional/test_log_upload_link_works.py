"""
Functional test (2): Confirm the upload link works as expected.

Precondition: test (1) must have run in this session (or the upload URL can
be supplied via the UPLOAD_URL environment variable for standalone execution).

Steps:
  1. Obtain the one-time upload URL (from upload_url_store or env var).
  2. HTTP PUT a minimal dummy .zip file to the URL.
  3. Assert the portal responds with HTTP 200.
  4. Assert the uploaded file exists in S3 at the expected key.
"""

import io
import logging
import os
import zipfile
import requests

from config import config
from tests.aws_utils import s3_object_exists

logger = logging.getLogger(__name__)


def _make_dummy_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.log", "MNO portal functional test log content")
    return buf.getvalue()


def test_log_upload_link_works(
    test_alert_reference,
    safe_alert,
    mno_id,
    upload_url_store,
):

    upload_url = upload_url_store.get("url") or os.environ.get("UPLOAD_URL")

    assert upload_url, (
        "No upload URL available. Either run test (1) first in this session "
        "or set the UPLOAD_URL environment variable."
    )
    logger.info("Step 1: using upload URL: %s", upload_url)

    logger.info("Step 2: uploading dummy .zip via PUT to the portal")

    dummy_zip = _make_dummy_zip()
    response = requests.put(
        upload_url,
        data=dummy_zip,
        headers={"Content-Type": "application/zip"},
        timeout=30,
    )

    logger.info(
        "PUT response: HTTP %s — %s",
        response.status_code,
        response.text[:200],
    )

    assert response.status_code == 200, (
        f"Expected HTTP 200 from the upload endpoint, got {response.status_code}. "
        f"Response body: {response.text[:500]}"
    )
    logger.info("Step 3 PASSED: portal returned HTTP 200")

    logger.info("Step 4: checking S3 for uploaded object")

    expected_key = f"received/logs/{safe_alert}/CBC_{safe_alert}_{mno_id}.zip"
    assert s3_object_exists(expected_key), (
        f"Expected S3 object not found: s3://{config['log_bucket_name']}/{expected_key}"
    )
    logger.info("Step 4 PASSED: object found in S3 at %s", expected_key)
