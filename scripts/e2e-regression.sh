#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-18000}"
BACKEND_URL="${BACKEND_URL:-http://$BACKEND_HOST:$BACKEND_PORT}"
DB_PATH="${DANOTE_DB_PATH:-$ROOT_DIR/test-data/tmp/e2e-regression.sqlite3}"

BACKEND_PID=""

log() {
  printf '[e2e-regression] %s\n' "$1"
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

start_backend() {
  mkdir -p "$(dirname "$DB_PATH")"
  log "starting backend with DANOTE_DB_PATH=$DB_PATH"
  (
    cd "$BACKEND_DIR"
    export DANOTE_DB_PATH="$DB_PATH"
    export DANOTE_HOST="$BACKEND_HOST"
    export DANOTE_PORT="$BACKEND_PORT"
    exec ./.venv/bin/python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) &
  BACKEND_PID=$!
}

stop_backend() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  BACKEND_PID=""
}

wait_for_backend() {
  for _ in {1..40}; do
    if curl -fsS "$BACKEND_URL/api/health" >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done
  log "backend did not become reachable"
  exit 1
}

initialize_db() {
  mkdir -p "$(dirname "$DB_PATH")"
  (
    cd "$BACKEND_DIR"
    PYTHONPATH=. ./.venv/bin/python - "$DB_PATH" <<'PY'
from pathlib import Path
import sys

from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data

db_path = Path(sys.argv[1])
apply_migrations(db_path)
seed_starter_data(db_path)
PY
  )
}

assert_kat_saved() {
  local response
  response="$(curl -fsS "$BACKEND_URL/api/wordbank/lemmas/kat")"
  python3 - "$response" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["lemma"] == "kat"
PY
}

add_kat() {
  local response
  response="$(curl -fsS -X POST "$BACKEND_URL/api/wordbank/lexemes" -H 'Content-Type: application/json' -d '{"surface_token":"kat","lemma_candidate":"kat"}')"
  python3 - "$response" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["status"] in {"inserted", "exists"}
PY
}

main() {
  if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    log "missing backend virtualenv: $BACKEND_DIR/.venv/bin/python"
    exit 1
  fi

  rm -f "$DB_PATH"
  initialize_db

  start_backend
  wait_for_backend
  log "health check reachable"

  add_kat
  log "add-word flow passed"

  stop_backend
  log "backend restarted for persistence check"

  start_backend
  wait_for_backend
  assert_kat_saved
  log "restart persistence check passed"

  stop_backend
  log "e2e regression complete"
}

main "$@"
