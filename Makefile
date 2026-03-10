.PHONY: help setup-backend setup-backend-search setup-frontend setup lint lint-backend maintainability-check test pytest-backend test-backend-fast test-backend-unit test-backend-api test-backend-medium test-backend-slow test-backend-perf test-frontend docs-smoke agent-verify dev

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PY := $(BACKEND_DIR)/.venv/bin/python
BACKEND_PYTEST := PYTHONPATH=. $(BACKEND_DIR)/.venv/bin/pytest
BACKEND_TEST_UNIT_DIRS := tests/use_cases tests/services tests/bootstrap tests/db
BACKEND_TEST_API_DIR := tests/api
BACKEND_TEST_MEDIUM_DIR := tests/system/test_reliability.py
BACKEND_TEST_SLOW_DIR := tests/system/test_regression_fixtures.py
BACKEND_TEST_PERF_DIR := tests/system/test_wordbank_performance_smoke.py
export PATH := $(HOME)/.local/bin:$(PATH)

help:
	@echo "Available targets:"
	@echo "  setup-backend       Create backend venv and install requirements.lock.txt"
	@echo "  setup-backend-search Create backend venv and install search-only requirements (no DaCy)"
	@echo "  setup-frontend      Install frontend dependencies"
	@echo "  setup               Run setup-backend and setup-frontend"
	@echo "  lint                Run frontend lint and backend lint checks"
	@echo "  maintainability-check Run file size budget guardrails"
	@echo "  pytest-backend      Run backend pytest with ARGS passthrough"
	@echo "  test-backend-fast   Run fast backend unit + API tests"
	@echo "  test-backend-unit   Run fast backend unit tests"
	@echo "  test-backend-api    Run backend API contract tests"
	@echo "  test-backend-medium Run backend system integration tests"
	@echo "  test-backend-slow   Run backend slow regression fixture tests"
	@echo "  test-backend-perf   Run backend performance smoke checks"
	@echo "  test-frontend       Run frontend tests"
	@echo "  test                Run backend + frontend tests"
	@echo "  docs-smoke          Run command smoke checks used by documentation"
	@echo "  agent-verify        Run full agent self-verification pipeline"
	@echo "  dev                 Start backend + frontend via scripts/run-project.sh"

setup-backend:
	cd $(BACKEND_DIR) && python3 -m venv .venv
	$(BACKEND_PY) -m pip install --upgrade pip
	$(BACKEND_PY) -m pip install -r $(BACKEND_DIR)/requirements.lock.txt

setup-backend-search:
	cd $(BACKEND_DIR) && python3 -m venv .venv
	$(BACKEND_PY) -m pip install --upgrade pip
	$(BACKEND_PY) -m pip install -r $(BACKEND_DIR)/requirements.search.txt

setup-frontend:
	cd $(FRONTEND_DIR) && npm ci

setup: setup-backend setup-frontend

lint:
	$(MAKE) maintainability-check
	cd $(FRONTEND_DIR) && npm run lint
	$(MAKE) lint-backend

maintainability-check:
	./scripts/check-maintainability-budgets.sh

lint-backend:
	cd $(BACKEND_DIR) && .venv/bin/python -m compileall -q app
	cd $(BACKEND_DIR) && .venv/bin/python -m ruff check app/bootstrap app/core app/db app/api/routes/_runtime.py app/api/routes/_use_case_factories.py app/api/routes/root.py app/api/routes/analyze.py app/api/routes/sentencebank.py app/api/routes/wordbank.py app/main.py
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python -m mypy app/bootstrap app/core app/db app/api/routes/_runtime.py app/api/routes/_use_case_factories.py

pytest-backend:
	bash ./scripts/pytest-backend.sh $(ARGS)

test-backend-fast: test-backend-unit test-backend-api

test-backend-unit:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q $(BACKEND_TEST_UNIT_DIRS)

test-backend-api:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q $(BACKEND_TEST_API_DIR)

test-backend-medium:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q $(BACKEND_TEST_MEDIUM_DIR)

test-backend-slow:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q $(BACKEND_TEST_SLOW_DIR)

test-backend-perf:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q $(BACKEND_TEST_PERF_DIR)

test-frontend:
	cd $(FRONTEND_DIR) && npm test -- --run

test: test-backend-fast test-frontend

docs-smoke:
	./scripts/docs-smoke.sh

dev:
	./scripts/run-project.sh

agent-verify:
	./scripts/agent-self-verify.sh
