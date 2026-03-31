.DEFAULT_GOAL := help
SHELL = bash
DAG_OUTPUT ?= $(CURDIR)/dvc_dag.png


.PHONY: help
help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: install
install: ## install dependencies
	uv sync

.PHONY: lint
lint: ## lint code
	uv run ruff format src tests
	uv run ruff check --fix src tests

.PHONY: test
test: ## run all tests
	uv run pytest tests

.PHONY: typing
typing: ## check types
	uv run ty check

.PHONY: dag
dag: ## render the fixture DAG into ./dvc_dag.png
	tmpdir=$$(mktemp -d); \
	cd tests/fixtures/dvc_workspace && \
	DVC_GLOBAL_CONFIG_DIR="$$tmpdir/.dvc-global" \
	DVC_SITE_CACHE_DIR="$$tmpdir/.dvc-site-cache" \
	uv run dvc-dag --out "$(DAG_OUTPUT)"
