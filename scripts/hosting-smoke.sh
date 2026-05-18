#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_URL="${HOSTING_SMOKE_HEALTH_URL:-http://127.0.0.1:8000/api/health}"
SPA_URL="${HOSTING_SMOKE_SPA_URL:-http://127.0.0.1:8000/}"
TIMEOUT_SECONDS="${HOSTING_SMOKE_TIMEOUT_SECONDS:-90}"
CREATED_ENV_FILE="0"

log() {
  printf '[hosting-smoke] %s\n' "$1"
}

fail_with_logs() {
  printf '[hosting-smoke] ERROR: %s\n' "$1" >&2
  (
    cd "$ROOT_DIR"
    docker compose ps >&2 || true
    docker compose logs --tail=80 app >&2 || true
  )
  exit 1
}

cd "$ROOT_DIR"
if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.local" ]]; then
  log "using .env.local as temporary Docker env file for local smoke"
  cp "$ROOT_DIR/.env.local" "$ROOT_DIR/.env"
  CREATED_ENV_FILE="1"
fi

cleanup() {
  if [[ "$CREATED_ENV_FILE" == "1" ]]; then
    rm -f "$ROOT_DIR/.env"
  fi
}
trap cleanup EXIT

log "building and starting Docker services"
docker compose up -d --build

log "waiting for backend health at $HEALTH_URL"
deadline=$((SECONDS + TIMEOUT_SECONDS))
until curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    fail_with_logs "backend health check did not pass within ${TIMEOUT_SECONDS}s"
  fi
  sleep 2
done
log "backend health: ok"

log "checking SPA root at $SPA_URL"
if ! curl -fsS --max-time 5 "$SPA_URL" | grep -qi '<html'; then
  fail_with_logs "SPA root did not return HTML"
fi
log "SPA root: ok"

log "checking bundled English lexicon"
if ! docker compose exec -T app python - <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("/app/backend/resources/dictionaries/english_wiki.sqlite")
if not db_path.exists():
    raise SystemExit("English lexicon SQLite is missing")
with sqlite3.connect(db_path) as conn:
    count = conn.execute("SELECT COUNT(*) FROM en_forms").fetchone()[0]
    has_book = conn.execute(
        "SELECT 1 FROM en_forms WHERE form_lower = ? LIMIT 1",
        ("book",),
    ).fetchone()
if count < 1000 or has_book is None:
    raise SystemExit(f"English lexicon is incomplete: en_forms={count}")
PY
then
  fail_with_logs "bundled English lexicon check failed"
fi
log "English lexicon: ok"

log "hosting smoke passed"
