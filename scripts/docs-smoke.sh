#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[docs-smoke] %s\n' "$1"
}

log "checking script syntax"
bash -n "$ROOT_DIR/scripts/run-project.sh"
bash -n "$ROOT_DIR/scripts/e2e-regression.sh"
bash -n "$ROOT_DIR/scripts/hosting-check.sh"
bash -n "$ROOT_DIR/scripts/hosting-smoke.sh"
python3 -m py_compile "$ROOT_DIR/scripts/dev-app.py"

log "running bootstrap script tests"
bash "$ROOT_DIR/scripts/tests/test-run-project-bootstrap.sh"
python3 "$ROOT_DIR/scripts/tests/test-dev-app.py"

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
    make test-backend-fast
  else
    bash "$ROOT_DIR/scripts/pytest-backend.sh" -q tests/use_cases tests/services tests/bootstrap tests/db tests/api
  fi
)

log "documentation command smoke checks passed"
