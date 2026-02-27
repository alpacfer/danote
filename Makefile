.PHONY: help setup-backend setup-frontend setup lint lint-backend test test-backend-unit test-backend-medium test-backend-slow test-frontend docs-smoke agent-verify dev

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PY := $(BACKEND_DIR)/.venv/bin/python
BACKEND_PYTEST := PYTHONPATH=. $(BACKEND_DIR)/.venv/bin/pytest

help:
	@echo "Available targets:"
	@echo "  setup-backend       Create backend venv and install requirements.lock.txt"
	@echo "  setup-frontend      Install frontend dependencies"
	@echo "  setup               Run setup-backend and setup-frontend"
	@echo "  lint                Run frontend lint and backend lint checks"
	@echo "  test-backend-unit   Run fast backend unit tests"
	@echo "  test-backend-medium Run backend medium integration tests"
	@echo "  test-backend-slow   Run backend slow regression fixture tests"
	@echo "  test-frontend       Run frontend tests"
	@echo "  test                Run backend + frontend tests"
	@echo "  docs-smoke          Run command smoke checks used by documentation"
	@echo "  agent-verify        Run full agent self-verification pipeline"
	@echo "  dev                 Start backend + frontend via scripts/run-project.sh"

setup-backend:
	cd $(BACKEND_DIR) && python3 -m venv .venv
	$(BACKEND_PY) -m pip install --upgrade pip
	$(BACKEND_PY) -m pip install -r $(BACKEND_DIR)/requirements.lock.txt

setup-frontend:
	cd $(FRONTEND_DIR) && npm ci

setup: setup-backend setup-frontend

lint:
	cd $(FRONTEND_DIR) && npm run lint
	$(MAKE) lint-backend

lint-backend:
	PYTHONPATH=$(BACKEND_DIR) python3 -m compileall -q $(BACKEND_DIR)/app
	@if python3 -c "import ruff" >/dev/null 2>&1; then \
		python3 -m ruff check $(BACKEND_DIR)/app/services/use_cases $(BACKEND_DIR)/app/api/schemas $(BACKEND_DIR)/app/api/routes/analyze.py $(BACKEND_DIR)/app/api/routes/wordbank.py; \
	else \
		echo "[lint-backend] ruff not installed; skipping ruff check"; \
	fi

test-backend-unit:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_typo_engine_unit.py tests/test_token_classifier_unit.py tests/test_token_filter_unit.py tests/test_use_cases_unit.py

test-backend-medium:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_reliability.py tests/test_wordbank_endpoint.py

test-backend-slow:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/pytest -q tests/test_regression_fixtures.py

test-frontend:
	cd $(FRONTEND_DIR) && npm test -- --run

test: test-backend-unit test-frontend

docs-smoke:
	./scripts/docs-smoke.sh

dev:
	./scripts/run-project.sh

agent-verify:
	./scripts/agent-self-verify.sh
