.PHONY: install dev backend frontend test lint build

install:
	cd backend && uv venv -q .venv --python 3.11 && uv pip install --python .venv/bin/python -e ".[dev]"
	cd frontend && npm ci

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 backend frontend

test:
	cd backend && .venv/bin/pytest -q
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npx oxlint src && npx tsc -b

build:
	cd frontend && npm run build
