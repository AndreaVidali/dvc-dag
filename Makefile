.DEFAULT_GOAL := help
SHELL = bash
BUILD_OUTPUT_DIR ?= dist
SMOKE_VENV ?= /tmp/dvc-dag-smoke-venv
TOML_FILES := pyproject.toml prek.toml
MD_FILES := README.md CHANGELOG.md

.PHONY: help
help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## install dependencies
	uv sync

.PHONY: hooks
hooks: ## install prek hooks
	uv run prek install --prepare-hooks --overwrite

.PHONY: format
format: ## format and autofix code
	uv run uv-sort pyproject.toml
	uv run taplo fmt $(TOML_FILES)
	uv run mbake format Makefile
	uv run mdformat $(MD_FILES)
	uv run ruff format src tests
	uv run ruff check --fix src tests

.PHONY: lint
lint: ## lint code without modifying files
	uv run uv-sort --check pyproject.toml
	uv run taplo fmt --check $(TOML_FILES)
	uv run mbake format --check Makefile
	uv run mbake validate Makefile
	uv run mdformat --check $(MD_FILES)
	uv run ruff check src tests

.PHONY: test
test: ## run all tests
	uv run pytest tests

.PHONY: typing
typing: ## check types
	uv run ty check

.PHONY: deptry
deptry: ## check dependency declarations
	uv run deptry .

.PHONY: check
check: ## run lint, typing, deptry, and tests
	$(MAKE) lint
	$(MAKE) typing
	$(MAKE) deptry
	$(MAKE) test

.PHONY: build
build: ## build wheel and sdist
	uv build --out-dir "$(BUILD_OUTPUT_DIR)"

.PHONY: smoke-wheel
smoke-wheel: ## install the built wheel into a temp venv and smoke-test it
	rm -rf "$(SMOKE_VENV)"
	.venv/bin/python -m venv "$(SMOKE_VENV)"
	uv pip install --python "$(SMOKE_VENV)/bin/python" "$(BUILD_OUTPUT_DIR)"/dvc_dag-*.whl
	"$(SMOKE_VENV)/bin/dvc-dag" --version
	"$(SMOKE_VENV)/bin/python" -m dvc_dag --help

.PHONY: release-check
release-check: ## run checks, build artifacts, and smoke-test the built wheel
	$(MAKE) check
	$(MAKE) build
	$(MAKE) smoke-wheel

.PHONY: sync-demo-dag
sync-demo-dag: ## copy the fixture DAG image into docs/
	.venv/bin/python scripts/sync_demo_dag.py

.PHONY: dag
dag: ## repro the fixture DAG stage and sync docs/dvc_project_dag.png
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	cd tests/fixtures/dvc_project && \
	PATH="$$PWD/../../../.venv/bin:$$PATH" \
	DVC_GLOBAL_CONFIG_DIR="$$tmpdir/.dvc-global" \
	DVC_SITE_CACHE_DIR="$$tmpdir/.dvc-site-cache" \
	../../../.venv/bin/dvc repro publish-project-dag --force
	$(MAKE) sync-demo-dag