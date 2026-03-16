.PHONY: help install install-dev test test-cov lint format typecheck check generate

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ──────────────────────────────────────────────
install: ## Install OCBC
	python3 -m pip install .

install-dev: ## Install with dev dependencies
	python3 -m pip install -e ".[dev]"
	pre-commit install

# ─── Testing ────────────────────────────────────────────
test: ## Run tests
	python3 -m pytest tests/ -v

test-cov: ## Run tests with 100% coverage requirement
	python3 -m pytest tests/ -v --cov=ocbc --cov-report=term-missing --cov-report=html --cov-fail-under=100

# ─── Code Quality ──────────────────────────────────────
lint: ## Run linter (ruff)
	python3 -m ruff check src/ tests/

format: ## Auto-format code (ruff)
	python3 -m ruff format src/ tests/
	python3 -m ruff check --fix src/ tests/

check: lint test-cov ## Run all checks (lint + test with 100% coverage)

# ─── Application Usage ─────────────────────────────────
generate: ## Run generation script for the baseline JSON
	mkdir -p baseline/historical
	python3 -m ocbc.generate --out baseline/ocbc_full_catalog_enriched.json
	@TIMESTAMP=$$(date -u +"%Y-%m-%dT%H-%M-%SZ"); \
	cp baseline/ocbc_full_catalog_enriched.json baseline/historical/ocbc_full_catalog_enriched_$${TIMESTAMP}.json
