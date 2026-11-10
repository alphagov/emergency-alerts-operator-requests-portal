import requests

from config import config


def test_index_page_still_reachable():
    resp = requests.get(f"{config['portal_url']}/index.html", timeout=30)
    assert resp.status_code == 200
    assert "Welcome to the Operator Portal" in resp.text
