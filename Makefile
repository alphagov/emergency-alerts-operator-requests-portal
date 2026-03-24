.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: bootstrap
bootstrap:
	mkdir -p functional-test-reports
	pip install -r requirements.txt

.PHONY: lint
lint:
	isort --check-only tests
	flake8 .
	black --check .

.PHONY: test-log-upload-request
test-log-upload-request: # Test (1): trigger upload request flow and verify invite email is received
	pytest -v \
	tests/functional/test_log_upload_request_flow.py \
	--junitxml=functional-test-reports/log-upload-request-flow

.PHONY: test-log-upload-link
test-log-upload-link: # Test (2): follow upload link and verify file lands in S3
	pytest -v \
	tests/functional/test_log_upload_link_works.py \
	--junitxml=functional-test-reports/log-upload-link-works

.PHONY: test-log-upload-single-use
test-log-upload-single-use: # Test (3): verify upload link cannot be reused
	pytest -v \
	tests/functional/test_log_upload_link_single_use.py \
	--junitxml=functional-test-reports/log-upload-link-single-use