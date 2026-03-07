.PHONY: help setup-backend setup-backend-search setup-frontend setup lint lint-backend maintainability-check test test-backend-unit test-backend-medium test-backend-slow test-backend-perf test-frontend docs-smoke agent-verify dev

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PY := $(BACKEND_DIR)/.venv/bin/python
BACKEND_PYTEST := PYTHONPATH=. $(BACKEND_DIR)/.venv/bin/pytest
export PATH := $(HOME)/.local/bin:$(PATH)

help:
	@echo "Available targets:"
	@echo "  setup-backend       Create backend venv and install requirements.lock.txt"
	@echo "  setup-backend-search Create backend venv and install search-only requirements (no DaCy)"
	@echo "  setup-frontend      Install frontend dependencies"
	@echo "  setup               Run setup-backend and setup-frontend"
	@echo "  lint                Run frontend lint and backend lint checks"
	@echo "  maintainability-check Run file size budget guardrails"
	@echo "  test-backend-unit   Run fast backend unit tests"
	@echo "  test-backend-medium Run backend medium integration tests"
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
	cd $(FRONTEND_DIR) && npm run lint
	$(MAKE) lint-backend

maintainability-check:
	./scripts/check-maintainability-budgets.sh

lint-backend:
	cd $(BACKEND_DIR) && .venv/bin/python -m compileall -q app
	cd $(BACKEND_DIR) && .venv/bin/python -m ruff check app/bootstrap app/core app/db app/api/routes/_runtime.py app/api/routes/_use_case_factories.py app/api/routes/root.py app/api/routes/analyze.py app/api/routes/sentencebank.py app/api/routes/wordbank.py app/main.py
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python -m mypy app/bootstrap app/core app/db app/api/routes/_runtime.py app/api/routes/_use_case_factories.py

test-backend-unit:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_typo_engine_unit.py tests/test_token_classifier_unit.py tests/test_token_filter_unit.py tests/test_cor_local_builder_unit.py tests/test_cor_local_service_unit.py tests/test_use_cases_unit.py tests/test_runtime_state_unit.py tests/test_repositories_unit.py

test-backend-medium:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_reliability.py tests/test_wordbank_endpoint.py

test-backend-slow:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_regression_fixtures.py

test-backend-perf:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_wordbank_performance_smoke.py

test-frontend:
	cd $(FRONTEND_DIR) && npm test -- --run

test: test-backend-unit test-frontend

docs-smoke:
	./scripts/docs-smoke.sh

dev:
	./scripts/run-project.sh

agent-verify:
	./scripts/agent-self-verify.sh
