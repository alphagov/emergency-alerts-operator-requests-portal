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

.PHONY: test-log-upload
test-log-upload: ## Run all log upload functional tests in a single session
	pytest -v \
	tests/functional/test_log_upload_request_flow.py \
	tests/functional/test_log_upload_link_works.py \
	tests/functional/test_log_upload_link_single_use.py \
	--junitxml=functional-test-reports/log-upload-full-flow