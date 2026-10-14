import logging

import requests

from config import config
from tests.aws_utils import (
    filter_cloudwatch_logs,
    make_truncated_zip_bytes,
    put_upload_tracking_record,
    s3_object_exists,
)

logger = logging.getLogger(__name__)


def _upload_url(mno_portal_id: str = "", broadcast_id: str = "") -> str:
    url = f"{config['portal_url']}/log-upload"
    params = []
    if mno_portal_id:
        params.append(f"mno={mno_portal_id}")
    if broadcast_id:
        params.append(f"broadcast_id={broadcast_id}")
    return url + ("?" + "&".join(params) if params else "")


def test_missing_mno_param(broadcast_id):
    resp = requests.put(_upload_url(broadcast_id=broadcast_id), data=b"x", timeout=30)
    assert resp.status_code == 400
    assert resp.headers.get("X-Error-Type") == "missing_mno"


def test_missing_broadcast_id_param(mno_portal_id):
    resp = requests.put(_upload_url(mno_portal_id=mno_portal_id), data=b"x", timeout=30)
    assert resp.status_code == 400
    assert resp.headers.get("X-Error-Type") == "missing_broadcast_id"


def test_wrong_http_method(mno_portal_id, broadcast_id):
    resp = requests.get(_upload_url(mno_portal_id, broadcast_id), timeout=30)
    assert resp.status_code == 403
    assert resp.headers.get("X-Error-Type") == "method_not_allowed"


def test_unknown_mno_or_broadcast(mno_portal_id, broadcast_id):
    resp = requests.put(_upload_url(mno_portal_id, broadcast_id), data=b"x", timeout=30)
    assert resp.status_code == 403
    assert resp.headers.get("X-Error-Type") == "invalid_request"


def test_expired_link(mno_portal_id, broadcast_id):
    put_upload_tracking_record(
        mno_portal_id, broadcast_id,
        s3_location=f"/received/logs/{broadcast_id}/CBC_TEST_00000000-0000Z_{broadcast_id}.zip",
        expires_in_seconds=-3600,
    )
    resp = requests.put(_upload_url(mno_portal_id, broadcast_id), data=b"x", timeout=30)
    assert resp.status_code == 403
    assert resp.headers.get("X-Error-Type") == "expired_link"


def test_already_used_link(mno_portal_id, broadcast_id):
    put_upload_tracking_record(
        mno_portal_id, broadcast_id,
        s3_location=f"/received/logs/{broadcast_id}/CBC_TEST_00000000-0000Z_{broadcast_id}.zip",
        used=True,
    )
    resp = requests.put(_upload_url(mno_portal_id, broadcast_id), data=b"x", timeout=30)
    assert resp.status_code == 403
    assert resp.headers.get("X-Error-Type") == "already_used"


def _rejected_content_case(mno_portal_id, broadcast_id, content: bytes):
    s3_key = f"received/logs/{broadcast_id}/CBC_TEST_00000000-0000Z_{broadcast_id}.zip"
    put_upload_tracking_record(mno_portal_id, broadcast_id, s3_location=f"/{s3_key}")

    resp = requests.put(_upload_url(mno_portal_id, broadcast_id), data=content, timeout=30)
    assert resp.status_code == 200, "Edge Lambda validates the key pattern, not content"
    assert s3_object_exists(s3_key)

    matches = filter_cloudwatch_logs(
        config["log_download_lambda_name"],
        filter_pattern=f'"{broadcast_id}"',
        since_minutes=5,
    )
    assert not any("Sent download notification" in m for m in matches), (
        "Internal notify should NOT fire for non-ZIP content"
    )


def test_non_zip_file_renamed_zip(mno_portal_id, broadcast_id):
    _rejected_content_case(mno_portal_id, broadcast_id, b"this is not a zip file")


def test_truncated_zip(mno_portal_id, broadcast_id):
    _rejected_content_case(mno_portal_id, broadcast_id, make_truncated_zip_bytes())


def test_empty_file(mno_portal_id, broadcast_id):
    _rejected_content_case(mno_portal_id, broadcast_id, b"")


def test_malformed_query_params(broadcast_id):
    resp = requests.put(
        f"{config['portal_url']}/log-upload?mno=%00%ff&broadcast_id={broadcast_id}",
        data=b"x", timeout=30,
    )
    assert resp.status_code in (400, 403), (
        f"Expected a graceful client error, got {resp.status_code}: {resp.text[:300]}"
    )
