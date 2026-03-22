#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# shellcheck source=./lib/bootstrap-common.sh
source "$ROOT_DIR/scripts/lib/bootstrap-common.sh"
BOOTSTRAP_LOG_PREFIX="run-project"

PYTHON_VERSION="${RUN_PROJECT_PYTHON_VERSION:-$BOOTSTRAP_PYTHON_VERSION_DEFAULT}"
NODE_MIN_VERSION="${RUN_PROJECT_NODE_MIN_VERSION:-20.19.0}"
MODEL_URL="${RUN_PROJECT_MODEL_URL:-$BOOTSTRAP_DACY_MODEL_URL_DEFAULT}"
MODEL_FILE="${RUN_PROJECT_MODEL_FILE:-$BOOTSTRAP_DACY_MODEL_FILE_DEFAULT}"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_LOG_FILE=""
PLATFORM_OS=""
BACKEND_HOST=""
BACKEND_PORT=""
FRONTEND_HOST=""
FRONTEND_PORT=""
VITE_BACKEND_URL=""
DANOTE_TRANSLATION_PROVIDER=""
DANOTE_GEMINI_MODEL=""
DANOTE_GEMINI_API_KEY=""
DANOTE_TRANSLATION_DEEPL_API_KEY=""

load_env_files() {
  local env_file
  for env_file in "$ROOT_DIR/.env" "$ROOT_DIR/.env.local"; do
    if [[ -f "$env_file" ]]; then
      bootstrap::log "loading env file: ${env_file#$ROOT_DIR/}"
      set -a
      # shellcheck disable=SC1090
      source "$env_file"
      set +a
    fi
  done
}

cleanup() {
  bootstrap::log "stopping services..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

configure_runtime() {
  BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
  BACKEND_PORT="${BACKEND_PORT:-8000}"
  FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
  FRONTEND_PORT="${FRONTEND_PORT:-4173}"
  VITE_BACKEND_URL="${VITE_BACKEND_URL:-http://$BACKEND_HOST:$BACKEND_PORT}"
  DANOTE_TRANSLATION_PROVIDER="${DANOTE_TRANSLATION_PROVIDER:-deepl}"
  DANOTE_GEMINI_MODEL="${DANOTE_GEMINI_MODEL:-gemini-3.1-flash-lite-preview}"
  DANOTE_GEMINI_API_KEY="${DANOTE_GEMINI_API_KEY:-${DANOTE_WORD_VERIFICATION_GEMINI_API_KEY:-}}"
  DANOTE_TRANSLATION_DEEPL_API_KEY="${DANOTE_TRANSLATION_DEEPL_API_KEY:-${DANOTE_DEEPL_API_KEY:-}}"
  BACKEND_LOG_FILE="${BACKEND_LOG_FILE:-$(mktemp -t danote-backend-log.XXXXXX)}"
}

is_disabled_value() {
  local normalized_value
  normalized_value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$normalized_value" in
    0|false|no)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

assert_supported_platform() {
  PLATFORM_OS="$(bootstrap::detect_os || true)"
  [[ -n "$PLATFORM_OS" ]] || bootstrap::die "unsupported operating system: ${DANOTE_BOOTSTRAP_OS_OVERRIDE:-$(uname -s)}. Supported platforms are macOS and Linux."
}

assert_frontend_runtime() {
  if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    bootstrap::print_node_install_help "$PLATFORM_OS" "$NODE_MIN_VERSION"
    bootstrap::die "node and npm must be installed before frontend bootstrap can run"
  fi

  local node_version
  node_version="$(bootstrap::node_version)"
  if ! bootstrap::node_version_at_least "$NODE_MIN_VERSION"; then
    bootstrap::print_node_install_help "$PLATFORM_OS" "$NODE_MIN_VERSION"
    bootstrap::die "detected Node.js $node_version but danote requires >= $NODE_MIN_VERSION"
  fi
}

backend_python_bin() {
  printf '%s\n' "$BACKEND_DIR/.venv/bin/python"
}

backend_env_reason() {
  local python_bin
  python_bin="$(backend_python_bin)"

  if [[ ! -x "$python_bin" ]]; then
    printf '%s\n' "missing backend interpreter"
    return 0
  fi

  local detected_python
  detected_python="$(bootstrap::python_minor_version "$python_bin" 2>/dev/null || true)"
  if [[ "$detected_python" != "$PYTHON_VERSION" ]]; then
    printf '%s\n' "backend venv uses Python ${detected_python:-unknown}, expected $PYTHON_VERSION"
    return 0
  fi

  if ! bootstrap::python_has_module "$python_bin" "uvicorn"; then
    printf '%s\n' "backend venv is missing uvicorn"
    return 0
  fi

  printf '%s\n' ""
}

recreate_backend_env() {
  local reason="$1"
  local python_bin
  python_bin="$(backend_python_bin)"
  local uv_bin
  uv_bin="$(bootstrap::ensure_uv)"

  bootstrap::log "${reason:-creating backend virtual environment}"
  bootstrap::log "ensuring Python $PYTHON_VERSION is available via uv"
  bootstrap::install_uv_python "$uv_bin" "$PYTHON_VERSION"

  if [[ -d "$BACKEND_DIR/.venv" ]]; then
    rm -rf "$BACKEND_DIR/.venv"
  fi

  bootstrap::create_uv_venv "$uv_bin" "$PYTHON_VERSION" "$BACKEND_DIR/.venv"
  bootstrap::install_locked_backend_deps "$uv_bin" "$python_bin" "$BACKEND_DIR/requirements.lock.txt"
  bootstrap::log "backend virtual environment is now managed with uv Python $PYTHON_VERSION"
}

ensure_backend_model() {
  local python_bin
  python_bin="$(backend_python_bin)"

  if is_disabled_value "${DANOTE_NLP_ENABLED:-1}"; then
    bootstrap::log "skipping NLP model bootstrap because DANOTE_NLP_ENABLED=${DANOTE_NLP_ENABLED:-1}"
    return
  fi

  local model_name="${DANOTE_NLP_MODEL:-$BOOTSTRAP_DACY_MODEL_NAME_DEFAULT}"
  if bootstrap::model_installed "$python_bin" "$model_name"; then
    bootstrap::log "NLP model ready: $model_name"
    return
  fi

  local uv_bin
  uv_bin="$(bootstrap::ensure_uv)"
  bootstrap::ensure_model_installed "$uv_bin" "$python_bin" "$ROOT_DIR" "$model_name" "$MODEL_URL" "$MODEL_FILE"
  bootstrap::log "NLP model ready: $model_name"
}

ensure_backend_env() {
  local reason
  reason="$(backend_env_reason)"
  if [[ -n "$reason" ]]; then
    recreate_backend_env "$reason"
  else
    bootstrap::log "backend virtual environment is ready"
  fi

  ensure_backend_model
}

ensure_frontend_env() {
  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    bootstrap::log "frontend node_modules found"
    return
  fi

  bootstrap::log "installing frontend dependencies"
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    (cd "$FRONTEND_DIR" && npm ci)
  else
    (cd "$FRONTEND_DIR" && npm install)
  fi
}

start_backend() {
  bootstrap::log "capturing backend logs in $BACKEND_LOG_FILE"
  : > "$BACKEND_LOG_FILE"
  bootstrap::log "starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
  bootstrap::log "translation provider: $DANOTE_TRANSLATION_PROVIDER"
  (
    cd "$BACKEND_DIR"
    export DANOTE_TRANSLATION_PROVIDER
    export DANOTE_GEMINI_MODEL
    export DANOTE_GEMINI_API_KEY
    export DANOTE_TRANSLATION_DEEPL_API_KEY
    exec ./.venv/bin/python -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
      >>"$BACKEND_LOG_FILE" 2>&1
  ) &
  BACKEND_PID=$!
}

print_backend_log_tail() {
  if [[ -f "$BACKEND_LOG_FILE" ]]; then
    bootstrap::log "recent backend log output:"
    tail -n 40 "$BACKEND_LOG_FILE" >&2 || true
  fi
}

wait_for_backend() {
  local health_url="http://$BACKEND_HOST:$BACKEND_PORT/api/health"
  for _ in {1..30}; do
    if curl -fsS "$health_url" >/dev/null 2>&1; then
      bootstrap::log "backend health check passed: $health_url"
      return
    fi
    if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      print_backend_log_tail
      bootstrap::die "backend exited before becoming healthy"
    fi
    sleep 1
  done

  print_backend_log_tail
  bootstrap::die "backend did not become healthy in time"
}

start_frontend() {
  bootstrap::log "starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
  (
    cd "$FRONTEND_DIR"
    export VITE_BACKEND_URL
    exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) &
  FRONTEND_PID=$!
}

main() {
  trap cleanup EXIT INT TERM

  load_env_files
  configure_runtime
  assert_supported_platform
  bootstrap::require_cmd curl
  assert_frontend_runtime
  ensure_backend_env
  ensure_frontend_env
  start_backend
  wait_for_backend
  start_frontend

  bootstrap::log "project running"
  bootstrap::log "frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
  bootstrap::log "backend:  http://$BACKEND_HOST:$BACKEND_PORT"
  bootstrap::log "press Ctrl+C to stop"

  wait "$BACKEND_PID" "$FRONTEND_PID"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
