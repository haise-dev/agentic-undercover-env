.PHONY: up down dev test lint format clean logs build help

help:           ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

up:             ## Start all services (Docker Compose)
	docker compose up -d

down:           ## Stop all services
	docker compose down

dev:            ## Start services in development mode with hot reload
	docker compose up --build

build:          ## Rebuild all Docker images
	docker compose build

test:           ## Run all tests (backend + frontend)
	cd apps/api && uv run pytest && cd ../web && npm run test

test-api:       ## Run backend tests only
	cd apps/api && uv run pytest

test-web:       ## Run frontend tests only
	cd apps/web && npm run test

lint:           ## Run linters (ruff + eslint)
	cd apps/api && uv run ruff check src/ && cd ../web && npm run lint

format:         ## Auto-format code (ruff + prettier)
	cd apps/api && uv run ruff format src/ && cd ../web && npm run format

clean:          ## Remove build artifacts and caches
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	rm -rf apps/api/.pytest_cache apps/api/.ruff_cache apps/api/htmlcov apps/api/.coverage
	rm -rf apps/web/.next apps/web/out apps/web/node_modules apps/api/.venv

logs:           ## Tail logs from all services
	docker compose logs -f

logs-api:       ## Tail API service logs only
	docker compose logs -f api

logs-web:       ## Tail web service logs only
	docker compose logs -f web

migrate:        ## Run database migrations (alembic upgrade head)
	cd apps/api && uv run alembic upgrade head
