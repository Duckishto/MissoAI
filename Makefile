# Cross-platform. The backend runs in Docker, so Windows, macOS and Linux
# all behave the same and no local Python is needed.

ifeq ($(OS),Windows_NT)
    MAKE_ENV = if not exist .env copy .env.example .env
else
    MAKE_ENV = test -f .env || cp .env.example .env
endif

.PHONY: help setup up down migrate seed dev web logs test shell reset psql

help:
	@echo.
	@echo   make setup     Build the API image and install frontend packages
	@echo   make up        Start Postgres and the API
	@echo   make migrate   Create the database tables
	@echo   make seed      Load the demo course and dev accounts
	@echo   make web       Start the frontend on :3000
	@echo   make logs      Tail the API logs
	@echo   make down      Stop everything
	@echo   make reset     Wipe the database and start clean
	@echo.

setup: ## Build the API image and install frontend packages
	$(MAKE_ENV)
	docker compose build api
	npm --prefix apps/web install

up: ## Start Postgres and the API
	docker compose up -d
	@echo API:  http://localhost:8000
	@echo Docs: http://localhost:8000/docs

down: ## Stop everything
	docker compose down

migrate: ## Create the database tables
	docker compose exec api alembic upgrade head

seed: ## Load the demo course and dev accounts
	docker compose exec api python scripts/seed_dev.py

web: ## Start the frontend
	npm --prefix apps/web run dev

logs: ## Tail the API logs
	docker compose logs -f api

test: ## Run the test suite inside the container
	docker compose exec -e RUN_DB_TESTS=1 api pytest -q

shell: ## Open a shell inside the API container
	docker compose exec api bash

psql: ## Open a database shell
	docker compose exec db psql -U postgres -d adaptive

reset: ## Wipe the database and start clean
	docker compose down -v
	docker compose up -d
	@echo Wait a few seconds, then run: make migrate
