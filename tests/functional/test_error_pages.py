import pytest
import requests

from config import config

PAGES = {
    "invalid-request.html": "Invalid Request",
    "link-expired.html": "Link Expired",
    "link-invalid.html": "Link No Longer Valid",
    "max-limit.html": "Maximum Limit Reached",
    "method-not-allowed.html": "Method Not Allowed",
    "error.html": "Something Went Wrong",
}


@pytest.mark.parametrize("page,expected_heading", PAGES.items(), ids=PAGES.keys())
def test_error_page_renders(page, expected_heading):
    resp = requests.get(f"{config['portal_url']}/{page}", timeout=30)
    assert resp.status_code == 200, f"{page} did not load: {resp.status_code}"
    assert expected_heading in resp.text, f"{page} missing expected heading '{expected_heading}'"


def test_nonexistent_path():
    resp = requests.get(f"{config['portal_url']}/does-not-exist", timeout=30)
    assert resp.status_code in (403, 404), f"Unexpected status for a missing path: {resp.status_code}"
