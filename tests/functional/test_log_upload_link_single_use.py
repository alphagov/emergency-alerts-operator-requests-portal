"""
Functional test (3): Confirm multiple uploads are not possible from a single link.

Precondition: test (2) must have run in this session (the upload link must have
been used at least once). The upload URL can also be supplied via UPLOAD_URL for
standalone execution against a link that has already been used.

Steps:
  1. Obtain the already-used one-time upload URL.
  2. HTTP PUT a dummy .zip file to the same URL again.
  3. Assert the portal responds with HTTP 403 and the response signals the link
     has already been used.
"""

import io
import logging
import os
import zipfile
import requests

logger = logging.getLogger(__name__)


def _make_dummy_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.log", "MNO portal functional test log content — second attempt")
    return buf.getvalue()


def test_log_upload_link_single_use(upload_url_store):
    """
    Attempt to reuse an already-consumed upload link and assert the portal
    refuses with HTTP 403 and an 'already_used' error type header.
    """
    upload_url = upload_url_store.get("url") or os.environ.get("UPLOAD_URL")

    assert upload_url, (
        "No upload URL available. Either run tests (1) and (2) first in this "
        "session or set the UPLOAD_URL environment variable to a previously-used link."
    )
    logger.info("Step 1: re-using upload URL: %s", upload_url)

    logger.info("Step 2: attempting second upload via PUT")

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

    assert response.status_code == 403, (
        f"Expected HTTP 403 (link already used), got {response.status_code}. "
        f"Response body: {response.text[:500]}"
    )
    logger.info("Step 3 PASSED: portal correctly refused second upload with HTTP 403")

    error_type = response.headers.get("X-Error-Type", "")
    assert error_type == "already_used", (
        f"Expected X-Error-Type header 'already_used', got '{error_type}'"
    )
    logger.info("Step 3 additional check PASSED: X-Error-Type is 'already_used'")

    assert "already been used" in response.text.lower(), (
        f"Expected response body to mention 'already been used', got: {response.text[:300]}"
    )
    logger.info("Step 3 body check PASSED: response body confirms link is exhausted")
