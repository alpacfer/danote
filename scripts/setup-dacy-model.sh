#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
MODEL_URL_DEFAULT="https://huggingface.co/chcaa/da_dacy_small_trf/resolve/0eadea074d5f637e76357c46bbd56451471d0154/da_dacy_small_trf-any-py3-none-any.whl"
MODEL_FILE_DEFAULT="da_dacy_small_trf-0.2.0-py3-none-any.whl"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
MODEL_NAME="${MODEL_NAME:-da_dacy_small_trf-0.2.0}"
MODEL_URL="${MODEL_URL:-$MODEL_URL_DEFAULT}"
MODEL_FILE="${MODEL_FILE:-$MODEL_FILE_DEFAULT}"
SKIP_SYSTEM_DEPS="${SKIP_SYSTEM_DEPS:-0}"
FORCE_RECREATE_VENV="${FORCE_RECREATE_VENV:-1}"
USE_UV="${USE_UV:-1}"

log() {
  printf '[setup-dacy-model] %s\n' "$1"
}

die() {
  printf '[setup-dacy-model] ERROR: %s\n' "$1" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

run_system_deps() {
  if [[ "$USE_UV" == "1" ]] && command -v uv >/dev/null 2>&1; then
    log "Skipping apt system deps because USE_UV=1 and uv is available"
    return
  fi

  if [[ "$SKIP_SYSTEM_DEPS" == "1" ]]; then
    log "Skipping system dependencies (SKIP_SYSTEM_DEPS=1)"
    return
  fi

  need_cmd sudo
  need_cmd apt-get
  local py_ver
  py_ver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [[ -z "$py_ver" ]]; then
    die "could not determine Python version from PYTHON_BIN=$PYTHON_BIN"
  fi

  log "Installing system dependencies (build-essential, python${py_ver}-venv, python${py_ver}-dev)"
  sudo apt-get update
  sudo apt-get install -y build-essential "python${py_ver}-venv" "python${py_ver}-dev"
}

create_venv() {
  if [[ "$USE_UV" == "1" ]] && command -v uv >/dev/null 2>&1; then
    log "Ensuring Python ${PYTHON_VERSION} is available via uv"
    uv python install "${PYTHON_VERSION}"
    if [[ "$FORCE_RECREATE_VENV" == "1" && -d "$VENV_DIR" ]]; then
      log "Removing existing backend venv at $VENV_DIR"
      rm -rf "$VENV_DIR"
    fi
    log "Creating backend venv with uv (Python ${PYTHON_VERSION})"
    uv venv --python "${PYTHON_VERSION}" "$VENV_DIR"
    return
  fi

  need_cmd "$PYTHON_BIN"
  if [[ "$FORCE_RECREATE_VENV" == "1" && -d "$VENV_DIR" ]]; then
    log "Removing existing backend venv at $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi
  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating backend venv with $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  else
    log "Using existing backend venv at $VENV_DIR"
  fi
}

install_backend_deps() {
  local py="$VENV_DIR/bin/python"
  if [[ "$USE_UV" == "1" ]] && command -v uv >/dev/null 2>&1; then
    log "Installing backend locked dependencies via uv"
    uv pip install --python "$py" -r "$BACKEND_DIR/requirements.lock.txt"
  else
    log "Upgrading pip/setuptools/wheel in backend venv"
    "$py" -m pip install --upgrade pip setuptools wheel
    log "Installing backend locked dependencies"
    "$py" -m pip install -r "$BACKEND_DIR/requirements.lock.txt"
  fi
}

download_model_wheel() {
  need_cmd curl
  local raw="$ROOT_DIR/da_dacy_small_trf-any-py3-none-any.whl"
  local fixed="$ROOT_DIR/$MODEL_FILE"
  log "Downloading model wheel to $raw"
  curl -L -o "$raw" "$MODEL_URL"
  log "Copying wheel to valid filename for pip: $fixed"
  cp "$raw" "$fixed"
}

install_model_wheel() {
  local py="$VENV_DIR/bin/python"
  local fixed="$ROOT_DIR/$MODEL_FILE"
  [[ -f "$fixed" ]] || die "model wheel not found: $fixed"
  log "Installing model wheel with --no-deps: $fixed"
  if [[ "$USE_UV" == "1" ]] && command -v uv >/dev/null 2>&1; then
    uv pip install --python "$py" --no-deps "$fixed"
  else
    "$py" -m pip install --no-deps "$fixed"
  fi
}

validate_model() {
  local py="$VENV_DIR/bin/python"
  log "Validating DaCy + model import"
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
  need_cmd rm
  need_cmd cp
  run_system_deps
  create_venv
  install_backend_deps
  download_model_wheel
  install_model_wheel
  validate_model
  log "Setup complete. Use this for backend startup:"
  print_env_hint
}

main "$@"
