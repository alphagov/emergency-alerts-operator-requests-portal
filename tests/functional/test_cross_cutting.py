import concurrent.futures
import logging
import uuid

import requests

from config import config
from tests.aws_utils import (
    delete_invite_tracking_record,
    get_invite_tracking_record,
    invoke_log_upload_lambda,
)

logger = logging.getLogger(__name__)


def test_concurrent_broadcasts_no_cross_contamination(mno_id, mno_label):
    """Two independent broadcasts for the same MNO, invited concurrently,
    must not clobber each other's tracking records."""
    broadcast_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    def invite(bid):
        return bid, invoke_log_upload_lambda(
            alert_reference=f"FUNCTIONAL-TEST-{uuid.uuid4().hex[:8].upper()}",
            mno_id=mno_id,
            broadcast_id=bid,
        )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = dict(pool.map(invite, broadcast_ids))

        for bid, response in results.items():
            assert response.get("body", {}).get("links_generated") == 1, f"broadcast {bid}: {response}"
            record = get_invite_tracking_record(mno_label, bid)
            assert record is not None, f"missing invite record for broadcast {bid}"
            assert record["AlertRef"]["S"] == f"{mno_label}#{bid}"
    finally:
        for bid in broadcast_ids:
            try:
                delete_invite_tracking_record(mno_label, bid)
            except Exception as e:
                logger.warning("Could not delete invite tracking record for %s: %s", bid, e)


def test_http_redirects_to_https():
    "Plain HTTP requests are redirected to HTTPS, not served insecurely."
    http_url = f"http://{config['portal_url'].removeprefix('https://')}/index.html"
    resp = requests.get(http_url, timeout=30, allow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308), (
        f"Expected a redirect to HTTPS, got {resp.status_code}"
    )
    assert resp.headers.get("Location", "").startswith("https://")
