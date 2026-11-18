"""
Uploads over 50 MB, or with no declared size, are rejected at the edge before any
tracking record is looked up and before anything reaches S3.
"""

from tests.unit._lambda_loader import load_lambda_module

MODULE_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda@edge-log-upload/files/edge-log-upload.py"
)
LIMIT = 50 * 1024 * 1024
QUERY = "mno=A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6&broadcast_id=broadcast-123"


def _load():
    module = load_lambda_module(MODULE_PATH, f"edge_log_upload_{id(object())}", env={})
    module.ddb.get_item.return_value = {
        "Item": {
            "Used": {"BOOL": False},
            "S3Location": {"S": "/received/logs/broadcast-123/CBC_EE_x_broadcast-123.zip"},
        }
    }
    return module


def _request(content_length=None):
    req = {"method": "PUT", "querystring": QUERY, "headers": {}}
    if content_length is not None:
        req["headers"]["content-length"] = [{"key": "Content-Length", "value": content_length}]
    return req


def _error_type(response):
    return response["headers"]["x-error-type"][0]["value"]


def test_upload_at_the_limit_is_accepted():
    module = _load()
    result = module._handle_viewer_request(_request(str(LIMIT)))
    assert result["uri"].startswith("/received/logs/")


def test_upload_over_the_limit_is_rejected_before_any_lookup():
    module = _load()
    result = module._handle_viewer_request(_request(str(LIMIT + 1)))
    assert result["status"] == "413"
    assert _error_type(result) == "file_too_large"
    module.ddb.get_item.assert_not_called()


def test_upload_without_a_declared_size_is_rejected():
    module = _load()
    result = module._handle_viewer_request(_request())
    assert result["status"] == "411"
    assert _error_type(result) == "length_required"
    module.ddb.get_item.assert_not_called()


def test_upload_with_an_invalid_size_is_rejected():
    module = _load()
    result = module._handle_viewer_request(_request("not-a-number"))
    assert result["status"] == "400"
    assert _error_type(result) == "invalid_content_length"


def test_empty_upload_passes_the_size_check():
    """Empty files are allowed through here; the post-upload ZIP check rejects them."""
    module = _load()
    result = module._handle_viewer_request(_request("0"))
    assert result["uri"].startswith("/received/logs/")
