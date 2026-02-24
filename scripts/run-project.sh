#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
VITE_BACKEND_URL="${VITE_BACKEND_URL:-http://$BACKEND_HOST:$BACKEND_PORT}"

BACKEND_PID=""
FRONTEND_PID=""

log() {
  printf '[run-project] %s\n' "$1"
}

cleanup() {
  log "stopping services..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

ensure_backend_env() {
  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    log "backend virtual environment found"
    return
  fi

  log "creating backend virtual environment"
  if python3 -m venv "$BACKEND_DIR/.venv" >/dev/null 2>&1; then
    "$BACKEND_DIR/.venv/bin/python" -m pip install --upgrade pip
    "$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements-dev.txt"
    return
  fi

  local uv_bin="${HOME}/.local/bin/uv"
  if [[ ! -x "$uv_bin" ]]; then
    log "python3 -m venv unavailable, installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi

  "${HOME}/.local/bin/uv" venv --clear "$BACKEND_DIR/.venv"
  "${HOME}/.local/bin/uv" pip install \
    --python "$BACKEND_DIR/.venv/bin/python" \
    -r "$BACKEND_DIR/requirements-dev.txt"
}

ensure_frontend_env() {
  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    log "frontend node_modules found"
    return
  fi

  log "installing frontend dependencies"
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    (cd "$FRONTEND_DIR" && npm ci)
  else
    (cd "$FRONTEND_DIR" && npm install)
  fi
}

start_backend() {
  log "starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
  (
    cd "$BACKEND_DIR"
    exec ./.venv/bin/python -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) &
  BACKEND_PID=$!
}

wait_for_backend() {
  local health_url="http://$BACKEND_HOST:$BACKEND_PORT/api/health"
  for _ in {1..30}; do
    if curl -fsS "$health_url" >/dev/null 2>&1; then
      log "backend health check passed: $health_url"
      return
    fi
    sleep 1
  done
  log "backend did not become healthy in time"
  exit 1
}

start_frontend() {
  log "starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
  (
    cd "$FRONTEND_DIR"
    export VITE_BACKEND_URL
    exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) &
  FRONTEND_PID=$!
}

main() {
  command -v python3 >/dev/null 2>&1 || {
    log "python3 is required"
    exit 1
  }
  command -v npm >/dev/null 2>&1 || {
    log "npm is required"
    exit 1
  }
  command -v curl >/dev/null 2>&1 || {
    log "curl is required"
    exit 1
  }

  ensure_backend_env
  ensure_frontend_env
  start_backend
  wait_for_backend
  start_frontend

  log "project running"
  log "frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
  log "backend:  http://$BACKEND_HOST:$BACKEND_PORT"
  log "press Ctrl+C to stop"

  wait "$BACKEND_PID" "$FRONTEND_PID"
}

main "$@"
