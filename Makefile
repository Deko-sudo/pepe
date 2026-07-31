.PHONY: help up down build rebuild logs ps test lint format typecheck migrate migration shell-api shell-db clean tradingview-wrapper-lint tradingview-wrapper-typecheck tradingview-wrapper-test tradingview-wrapper-build tradingview-wrapper-e2e tradingview-wrapper-provider-check

MINI_APP_BUILD_ID ?= $(shell git rev-parse --short=8 HEAD)
export MINI_APP_BUILD_ID

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services after database migrations
	docker compose up -d

down: ## Stop all services
	docker compose down

build: tradingview-wrapper-build ## Build all services
	docker compose build

rebuild: ## Rebuild all services without cache
	docker compose build --no-cache

logs: ## Show logs for all services
	docker compose logs -f

ps: ## Show running containers
	docker compose ps

test: tradingview-wrapper-test ## Run all tests
	cd apps/mini-app && npm test
	cd packages/quote-core && ../../apps/api/.venv/bin/python -m pytest
	cd apps/api && .venv/bin/python -m pytest
	cd apps/bot && .venv/bin/python -m pytest
	cd apps/worker && .venv/bin/python -m pytest

lint: tradingview-wrapper-lint ## Run linters
	cd apps/mini-app && npm run lint
	cd packages/quote-core && ../../apps/api/.venv/bin/ruff check .
	cd apps/api && .venv/bin/ruff check .
	cd apps/bot && .venv/bin/ruff check .
	cd apps/worker && .venv/bin/ruff check .

format: ## Format code
	cd apps/mini-app && npm run lint -- --fix
	cd packages/quote-core && ../../apps/api/.venv/bin/ruff format .
	cd apps/api && .venv/bin/ruff format .
	cd apps/bot && .venv/bin/ruff format .
	cd apps/worker && .venv/bin/ruff format .

typecheck: tradingview-wrapper-typecheck ## Run type checkers
	cd apps/mini-app && npm run typecheck
	cd packages/quote-core && ../../apps/api/.venv/bin/mypy src tests
	cd apps/api && .venv/bin/mypy .
	cd apps/bot && .venv/bin/mypy .
	cd apps/worker && .venv/bin/mypy .

migrate: ## Run database migrations
	cd apps/api && .venv/bin/alembic upgrade head

migration: ## Create new migration
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(msg)"

shell-api: ## Open API shell
	docker compose exec api bash

shell-db: ## Open database shell
	docker compose exec postgres psql -U pepe -d pepe

clean: ## Clean build artifacts
	rm -rf apps/mini-app/dist
	rm -rf apps/api/dist
	rm -rf apps/bot/dist
	rm -rf apps/worker/dist
	docker compose down -v --rmi local

tradingview-wrapper-lint: ## Lint static TradingView wrapper
	cd apps/tradingview-wrapper && npm run lint

tradingview-wrapper-typecheck: ## Typecheck static TradingView wrapper
	cd apps/tradingview-wrapper && npm run typecheck

tradingview-wrapper-test: tradingview-wrapper-build ## Test static TradingView wrapper
	cd apps/tradingview-wrapper && npm test

tradingview-wrapper-build: ## Build static TradingView wrapper
	cd apps/tradingview-wrapper && npm run build

tradingview-wrapper-e2e: tradingview-wrapper-build ## Run isolated wrapper browser tests
	cd apps/tradingview-wrapper && npm run e2e

tradingview-wrapper-provider-check: ## Compare observed official TradingView script hash
	cd apps/tradingview-wrapper && npm run provider-check
