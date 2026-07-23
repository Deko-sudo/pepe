.PHONY: help up down build rebuild logs ps test lint format typecheck migrate migration shell-api shell-db clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all services
	docker compose build

rebuild: ## Rebuild all services without cache
	docker compose build --no-cache

logs: ## Show logs for all services
	docker compose logs -f

ps: ## Show running containers
	docker compose ps

test: ## Run all tests
	cd apps/mini-app && npm test
	cd apps/api && .venv/bin/python -m pytest
	cd apps/bot && .venv/bin/python -m pytest
	cd apps/worker && .venv/bin/python -m pytest

lint: ## Run linters
	cd apps/mini-app && npm run lint
	cd apps/api && .venv/bin/ruff check .
	cd apps/bot && .venv/bin/ruff check .
	cd apps/worker && .venv/bin/ruff check .

format: ## Format code
	cd apps/mini-app && npm run lint -- --fix
	cd apps/api && ruff format .
	cd apps/bot && ruff format .
	cd apps/worker && ruff format .

typecheck: ## Run type checkers
	cd apps/mini-app && npm run typecheck
	cd apps/api && .venv/bin/mypy .
	cd apps/bot && .venv/bin/mypy .
	cd apps/worker && .venv/bin/mypy .

migrate: ## Run database migrations
	cd apps/api && alembic upgrade head

migration: ## Create new migration
	cd apps/api && alembic revision --autogenerate -m "$(msg)"

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
