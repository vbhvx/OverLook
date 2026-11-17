# OverLook developer commands. `make help` lists them.
PY ?= .venv/bin/python
# A separate database: the contract suite TRUNCATEs its tables between tests.
TEST_DB ?= postgresql+asyncpg://overlook:overlook@localhost:5432/overlook_test

.PHONY: help install dev api worker web test test-pg lint fmt migrate up up-obs down logs

help:  ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:  ## Install backend (venv) and frontend dependencies
	python3 -m venv .venv && $(PY) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci

api:  ## Run the API with the in-memory store and embedded scheduler
	$(PY) -m uvicorn backend.app.main:app --reload --port 8000

worker:  ## Run the standalone ingestion worker (needs DATABASE_URL)
	$(PY) -m backend.app.worker

web:  ## Run the Vite dev server (proxies /api to :8000)
	cd frontend && npm run dev

test:  ## Backend tests (memory store) + frontend tests
	$(PY) -m pytest --cov
	cd frontend && npm test

test-pg:  ## Backend tests including the PostGIS contract suite (`make up` first)
	-docker compose exec -T postgis createdb -U overlook overlook_test 2>/dev/null
	DATABASE_URL=$(TEST_DB) $(PY) -m alembic -c backend/alembic.ini upgrade head
	OVERLOOK_TEST_DATABASE_URL=$(TEST_DB) $(PY) -m pytest --cov

lint:  ## Lint and type-check everything
	$(PY) -m ruff check backend
	cd frontend && npm run lint && npm run typecheck

migrate:  ## Apply database migrations (needs DATABASE_URL)
	$(PY) -m alembic -c backend/alembic.ini upgrade head

up:  ## Start the full stack in Docker (UI on http://localhost:8080)
	docker compose up --build -d

up-obs:  ## Full stack + Prometheus (:9090) + Grafana (:3001)
	docker compose --profile observability up --build -d

down:  ## Stop the stack
	docker compose --profile observability down

logs:  ## Tail service logs
	docker compose logs -f api worker
