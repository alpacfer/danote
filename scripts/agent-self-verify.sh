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
  bash ./scripts/pytest-backend.sh -q tests/use_cases
)

log "agent self-verification passed"
