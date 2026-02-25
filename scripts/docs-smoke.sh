#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[docs-smoke] %s\n' "$1"
}

log "checking script syntax"
bash -n "$ROOT_DIR/scripts/run-project.sh"
bash -n "$ROOT_DIR/scripts/e2e-regression.sh"

log "running frontend lint"
(
  cd "$ROOT_DIR/frontend"
  npm run lint
)

log "running frontend tests"
(
  cd "$ROOT_DIR/frontend"
  npm test -- --run
)

log "running backend fast unit suite"
(
  if command -v make >/dev/null 2>&1; then
    cd "$ROOT_DIR"
    make test-backend-unit
  else
    cd "$ROOT_DIR/backend"
    PYTHONPATH=. .venv/bin/python -m pytest -q \
      tests/test_typo_engine_unit.py \
      tests/test_token_classifier_unit.py \
      tests/test_token_filter_unit.py \
      tests/test_use_cases_unit.py
  fi
)

log "documentation command smoke checks passed"
