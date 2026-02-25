#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[agent-self-verify] %s\n' "$1"
}

cd "$ROOT_DIR"

log "running lint"
make lint

log "running tests"
make test

log "running docs smoke checks"
make docs-smoke

log "running backend use-case verification"
(
  cd backend
  PYTHONPATH=. pytest -q tests/test_use_cases_unit.py
)

log "agent self-verification passed"
