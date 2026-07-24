"""
A failed/interrupted first PUT must not burn the one-time upload link —
the link should only be marked used once the origin (S3) confirms a successful write.
"""

from tests.unit._lambda_loader import load_lambda_module

MODULE_PATH = (
    "terraform/modules/operator-request-portal-lambda-functions/log-mgt-functions/"
    "lambda@edge-log-upload/files/edge-log-upload.py"
)

MNO_ID = "MNO1"
BROADCAST_ID = "broadcast-123"
TOKEN = "a" * 43  # same shape as secrets.token_urlsafe(32)


def _s3_uri(mno=MNO_ID, broadcast=BROADCAST_ID):
    return f"/received/logs/{broadcast}/CBC_{broadcast}_{mno}.zip"


def _load():
    return load_lambda_module(MODULE_PATH, f"edge_log_upload_{id(object())}", env={})


def _valid_item():
    return {
        "Used": {"BOOL": False},
        "S3Location": {"S": _s3_uri()},
        "MnoId": {"S": MNO_ID},
        "BroadcastId": {"S": BROADCAST_ID},
    }


def test_viewer_request_allows_valid_token_without_marking_it_used():
    """The viewer-request stage must forward the PUT but not consume the link — that
    is deferred to origin-response, once S3 confirms the write."""
    module = _load()
    module.ddb.get_item.return_value = {"Item": _valid_item()}

    req = {"method": "PUT", "querystring": f"token={TOKEN}"}
    result = module._handle_viewer_request(req)

    assert result["uri"] == _s3_uri()
    module.ddb.update_item.assert_not_called()


def test_viewer_request_rejects_link_already_marked_used():
    module = _load()
    module.ddb.get_item.return_value = {"Item": {**_valid_item(), "Used": {"BOOL": True}}}

    req = {"method": "PUT", "querystring": f"token={TOKEN}"}
    result = module._handle_viewer_request(req)

    assert result["status"] == "403"
    assert "already been used" in result["body"]


def test_origin_response_failure_leaves_link_unused_for_retry():
    """A non-2xx from the S3 origin (interrupted/failed write) must not mark the
    link as used, so a legitimate retry can still succeed."""
    module = _load()
    request = {
        "uri": _s3_uri(),
        "headers": {"x-upload-token": [{"key": "X-Upload-Token", "value": TOKEN}]},
    }

    result = module._handle_origin_response(request, {"status": "500"})

    assert result == {"status": "500"}
    module.ddb.update_item.assert_not_called()


def test_origin_response_success_marks_link_used_atomically():
    module = _load()
    request = {
        "uri": _s3_uri(),
        "headers": {"x-upload-token": [{"key": "X-Upload-Token", "value": TOKEN}]},
    }

    module._handle_origin_response(request, {"status": "200"})

    module.ddb.update_item.assert_called_once()
    _, kwargs = module.ddb.update_item.call_args
    assert kwargs["Key"] == {"RequestId": {"S": TOKEN}}
    assert "ConditionExpression" in kwargs


def test_origin_response_ignores_requests_without_a_token_header():
    """Requests that never went through our viewer-request validation (no token
    header attached) must not touch DynamoDB."""
    module = _load()

    result = module._handle_origin_response({"uri": "/some/other/path"}, {"status": "200"})

    assert result == {"status": "200"}
    module.ddb.update_item.assert_not_called()


def test_lambda_handler_dispatches_origin_response_only_after_viewer_request():
    """End-to-end: simulate CloudFront's two invocations for one PUT — viewer-request
    must not consume the link, and only a successful origin-response should."""
    module = _load()
    module.ddb.get_item.return_value = {"Item": _valid_item()}

    viewer_event = {
        "Records": [
            {
                "cf": {
                    "config": {"eventType": "viewer-request"},
                    "request": {
                        "method": "PUT",
                        "querystring": f"token={TOKEN}",
                    },
                }
            }
        ]
    }
    viewer_result = module.lambda_handler(viewer_event, None)
    assert viewer_result["uri"] == _s3_uri()
    module.ddb.update_item.assert_not_called()

    origin_event = {
        "Records": [
            {
                "cf": {
                    "config": {"eventType": "origin-response"},
                    "request": viewer_result,
                    "response": {"status": "200"},
                }
            }
        ]
    }
    module.lambda_handler(origin_event, None)
    module.ddb.update_item.assert_called_once()
    _, kwargs = module.ddb.update_item.call_args
    assert kwargs["Key"] == {"RequestId": {"S": TOKEN}}
