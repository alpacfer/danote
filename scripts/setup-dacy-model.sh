#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

# shellcheck source=./lib/bootstrap-common.sh
source "$ROOT_DIR/scripts/lib/bootstrap-common.sh"
BOOTSTRAP_LOG_PREFIX="setup-dacy-model"

PYTHON_VERSION="${PYTHON_VERSION:-$BOOTSTRAP_PYTHON_VERSION_DEFAULT}"
PYTHON_BIN="${PYTHON_BIN:-python${PYTHON_VERSION}}"
MODEL_NAME="${MODEL_NAME:-$BOOTSTRAP_DACY_MODEL_NAME_DEFAULT}"
MODEL_URL="${MODEL_URL:-$BOOTSTRAP_DACY_MODEL_URL_DEFAULT}"
MODEL_FILE="${MODEL_FILE:-$BOOTSTRAP_DACY_MODEL_FILE_DEFAULT}"
SKIP_SYSTEM_DEPS="${SKIP_SYSTEM_DEPS:-0}"
FORCE_RECREATE_VENV="${FORCE_RECREATE_VENV:-1}"
USE_UV="${USE_UV:-1}"

run_system_deps() {
  if [[ "$USE_UV" == "1" ]]; then
    bootstrap::log "Skipping apt system deps because USE_UV=1 bootstraps Python via uv"
    return
  fi

  if [[ "$SKIP_SYSTEM_DEPS" == "1" ]]; then
    bootstrap::log "Skipping system dependencies (SKIP_SYSTEM_DEPS=1)"
    return
  fi

  bootstrap::require_cmd sudo
  bootstrap::require_cmd apt-get
  local py_ver
  py_ver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [[ -z "$py_ver" ]]; then
    bootstrap::die "could not determine Python version from PYTHON_BIN=$PYTHON_BIN"
  fi

  bootstrap::log "Installing system dependencies (build-essential, python${py_ver}-venv, python${py_ver}-dev)"
  sudo apt-get update
  sudo apt-get install -y build-essential "python${py_ver}-venv" "python${py_ver}-dev"
}

create_venv() {
  if [[ "$USE_UV" == "1" ]]; then
    local uv_bin
    uv_bin="$(bootstrap::ensure_uv)"
    bootstrap::log "Ensuring Python ${PYTHON_VERSION} is available via uv"
    bootstrap::install_uv_python "$uv_bin" "${PYTHON_VERSION}"
    if [[ "$FORCE_RECREATE_VENV" == "1" && -d "$VENV_DIR" ]]; then
      bootstrap::log "Removing existing backend venv at $VENV_DIR"
      rm -rf "$VENV_DIR"
    fi
    bootstrap::log "Creating backend venv with uv (Python ${PYTHON_VERSION})"
    bootstrap::create_uv_venv "$uv_bin" "${PYTHON_VERSION}" "$VENV_DIR"
    return
  fi

  bootstrap::require_cmd "$PYTHON_BIN"
  if [[ "$FORCE_RECREATE_VENV" == "1" && -d "$VENV_DIR" ]]; then
    bootstrap::log "Removing existing backend venv at $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi
  if [[ ! -d "$VENV_DIR" ]]; then
    bootstrap::log "Creating backend venv with $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  else
    bootstrap::log "Using existing backend venv at $VENV_DIR"
  fi
}

install_backend_deps() {
  local py="$VENV_DIR/bin/python"
  if [[ "$USE_UV" == "1" ]]; then
    local uv_bin
    uv_bin="$(bootstrap::ensure_uv)"
    bootstrap::log "Installing backend locked dependencies via uv"
    bootstrap::install_locked_backend_deps "$uv_bin" "$py" "$BACKEND_DIR/requirements.lock.txt"
  else
    bootstrap::log "Upgrading pip/setuptools/wheel in backend venv"
    "$py" -m pip install --upgrade pip setuptools wheel
    bootstrap::log "Installing backend locked dependencies"
    "$py" -m pip install -r "$BACKEND_DIR/requirements.lock.txt"
  fi
}

install_model_wheel() {
  local py="$VENV_DIR/bin/python"
  if [[ "$USE_UV" == "1" ]]; then
    local uv_bin
    uv_bin="$(bootstrap::ensure_uv)"
    bootstrap::ensure_model_installed "$uv_bin" "$py" "$ROOT_DIR" "$MODEL_NAME" "$MODEL_URL" "$MODEL_FILE"
  else
    local fixed="$ROOT_DIR/$MODEL_FILE"
    if [[ ! -f "$fixed" ]]; then
      bootstrap::log "Downloading model wheel to $fixed"
      bootstrap::download_model_wheel "$ROOT_DIR" "$MODEL_URL" "$MODEL_FILE" >/dev/null
    fi
    bootstrap::log "Installing model wheel with --no-deps: $fixed"
    "$py" -m pip install --no-deps "$fixed"
  fi
}

validate_model() {
  local py="$VENV_DIR/bin/python"
  bootstrap::log "Validating DaCy + model import"
  "$py" - <<PY
import dacy
print("dacy:", dacy.__version__)
nlp = dacy.load("${MODEL_NAME}")
print("loaded:", nlp.meta.get("name"), nlp.meta.get("version"))
PY
}

print_env_hint() {
  cat <<EOF

export DANOTE_NLP_MODEL=${MODEL_NAME}
cd ${ROOT_DIR}
cd backend && . .venv/bin/activate && uvicorn app.main:app --reload
EOF
}

main() {
  bootstrap::require_cmd rm
  run_system_deps
  create_venv
  install_backend_deps
  install_model_wheel
  validate_model
  bootstrap::log "Setup complete. Use this for backend startup:"
  print_env_hint
}

main "$@"
