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

.PHONY: test-functional
test-functional: ## Run the full functional test suite against $ENVIRONMENT (default: development)
	pytest -v tests/functional --junitxml=functional-test-reports/functional-tests