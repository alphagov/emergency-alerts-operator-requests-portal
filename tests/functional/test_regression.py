import pytest
import requests

from config import config


def test_index_page_still_reachable():
    resp = requests.get(f"{config['portal_url']}/index.html", timeout=30)
    assert resp.status_code == 200
    assert "Welcome to the Operator Portal" in resp.text


@pytest.mark.skip(
    reason="CSR upload flow needs to be properly impltemented (Hence the commented out infra) "
    "nothing to regression-test yet."
)
def test_csr_upload_flow_unaffected():
    pass
