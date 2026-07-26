.PHONY: help install dev lint typecheck test test-belief test-er test-gates format clean up down migrate

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync

dev: ## Install all dependencies (including dev)
	uv sync --all-extras
	uv run pre-commit install

lint: ## Run linter (ruff)
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## Run type checker (mypy)
	uv run mypy core/ engine/ libs/ connectors/ services/api/ --ignore-missing-imports

format: ## Auto-format code
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run all tests
	uv run pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v --tb=short

test-belief: ## Run belief-purity suite (CI blocker)
	uv run pytest tests/suites/belief_purity/ -v --tb=long -m belief_purity

test-er: ## Run ER regression suite
	uv run pytest tests/suites/er_regression/ -v --tb=long -m er_regression

test-gates: ## Run gate integration tests
	uv run pytest tests/integration/test_gates.py -v --tb=long

up: ## Start local development environment
	docker compose up -d

down: ## Stop local development environment
	docker compose down

migrate: ## Run database migrations
	uv run alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="description")
	uv run alembic revision --autogenerate -m "$(msg)"

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist build *.egg-info htmlcov .coverage
