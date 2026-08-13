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
MNO_HEADER = {"x-upload-token": [{"key": "X-Upload-Token", "value": MNO_ID}]}


def _s3_uri(broadcast=BROADCAST_ID):
    return f"/received/logs/{broadcast}/CBC_THREE_20250512-0900Z_{broadcast}.zip"


def _load():
    return load_lambda_module(MODULE_PATH, f"edge_log_upload_{id(object())}", env={})


def test_viewer_request_allows_valid_link_without_marking_it_used():
    """The viewer-request stage must forward the PUT but not consume the link — that
    is deferred to origin-response, once S3 confirms the write."""
    module = _load()
    module.ddb.get_item.return_value = {
        "Item": {
            "Used": {"BOOL": False},
            "S3Location": {"S": _s3_uri()},
        }
    }

    req = {"method": "PUT", "querystring": f"mno={MNO_ID}&broadcast_id={BROADCAST_ID}"}
    result = module._handle_viewer_request(req)

    assert result["uri"] == _s3_uri()
    assert result["headers"]["x-upload-token"][0]["value"] == MNO_ID
    module.ddb.update_item.assert_not_called()


def test_viewer_request_rejects_link_already_marked_used():
    module = _load()
    module.ddb.get_item.return_value = {"Item": {"Used": {"BOOL": True}}}

    req = {"method": "PUT", "querystring": f"mno={MNO_ID}&broadcast_id={BROADCAST_ID}"}
    result = module._handle_viewer_request(req)

    assert result["status"] == "403"
    assert "already been used" in result["body"]


def test_origin_response_failure_leaves_link_unused_for_retry():
    """A non-2xx from the S3 origin (interrupted/failed write) must not mark the
    link as used, so a legitimate retry can still succeed."""
    module = _load()
    request = {"uri": _s3_uri(), "headers": MNO_HEADER}

    result = module._handle_origin_response(request, {"status": "500"})

    assert result == {"status": "500"}
    module.ddb.update_item.assert_not_called()


def test_origin_response_success_marks_link_used_atomically():
    module = _load()
    request = {"uri": _s3_uri(), "headers": MNO_HEADER}

    module._handle_origin_response(request, {"status": "200"})

    module.ddb.update_item.assert_called_once()
    _, kwargs = module.ddb.update_item.call_args
    assert kwargs["Key"] == {"RequestId": {"S": f"{MNO_ID}#{BROADCAST_ID}"}}
    assert "ConditionExpression" in kwargs


def test_origin_response_ignores_unrelated_uris():
    """Requests that don't match the upload key pattern must not touch DynamoDB."""
    module = _load()
    request = {"uri": "/some/other/path", "headers": MNO_HEADER}

    result = module._handle_origin_response(request, {"status": "200"})

    assert result == {"status": "200"}
    module.ddb.update_item.assert_not_called()


def test_origin_response_ignores_requests_without_the_mno_header():
    module = _load()
    request = {"uri": _s3_uri(), "headers": {}}

    result = module._handle_origin_response(request, {"status": "200"})

    assert result == {"status": "200"}
    module.ddb.update_item.assert_not_called()


def test_lambda_handler_dispatches_origin_response_only_after_viewer_request():
    """End-to-end: simulate CloudFront's two invocations for one PUT — viewer-request
    must not consume the link, and only a successful origin-response should."""
    module = _load()
    module.ddb.get_item.return_value = {
        "Item": {"Used": {"BOOL": False}, "S3Location": {"S": _s3_uri()}}
    }

    viewer_event = {
        "Records": [
            {
                "cf": {
                    "config": {"eventType": "viewer-request"},
                    "request": {
                        "method": "PUT",
                        "querystring": f"mno={MNO_ID}&broadcast_id={BROADCAST_ID}",
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
    assert kwargs["Key"] == {"RequestId": {"S": f"{MNO_ID}#{BROADCAST_ID}"}}
