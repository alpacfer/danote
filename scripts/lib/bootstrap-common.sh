#!/usr/bin/env bash

BOOTSTRAP_PYTHON_VERSION_DEFAULT="3.11"
BOOTSTRAP_DACY_MODEL_NAME_DEFAULT="da_dacy_small_trf-0.2.0"
BOOTSTRAP_DACY_MODEL_URL_DEFAULT="https://huggingface.co/chcaa/da_dacy_small_trf/resolve/0eadea074d5f637e76357c46bbd56451471d0154/da_dacy_small_trf-any-py3-none-any.whl"
BOOTSTRAP_DACY_MODEL_FILE_DEFAULT="da_dacy_small_trf-0.2.0-py3-none-any.whl"
BOOTSTRAP_UV_INSTALL_URL_DEFAULT="https://astral.sh/uv/install.sh"

bootstrap::prefix() {
  printf '%s' "${BOOTSTRAP_LOG_PREFIX:-bootstrap}"
}

bootstrap::log() {
  printf '[%s] %s\n' "$(bootstrap::prefix)" "$1" >&2
}

bootstrap::die() {
  printf '[%s] ERROR: %s\n' "$(bootstrap::prefix)" "$1" >&2
  exit 1
}

bootstrap::require_cmd() {
  command -v "$1" >/dev/null 2>&1 || bootstrap::die "missing required command: $1"
}

bootstrap::detect_os() {
  local detected_os="${DANOTE_BOOTSTRAP_OS_OVERRIDE:-$(uname -s)}"
  case "$detected_os" in
    Darwin|Linux)
      printf '%s\n' "$detected_os"
      ;;
    *)
      return 1
      ;;
  esac
}

bootstrap::uv_install_url() {
  printf '%s\n' "${UV_INSTALL_URL:-$BOOTSTRAP_UV_INSTALL_URL_DEFAULT}"
}

bootstrap::uv_bin_path() {
  if [[ -n "${UV_BIN:-}" ]]; then
    printf '%s\n' "$UV_BIN"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/uv" ]]; then
    printf '%s\n' "${HOME}/.local/bin/uv"
    return 0
  fi
  return 1
}

bootstrap::ensure_uv() {
  local uv_bin
  uv_bin="$(bootstrap::uv_bin_path || true)"
  if [[ -n "$uv_bin" ]]; then
    printf '%s\n' "$uv_bin"
    return 0
  fi

  bootstrap::require_cmd curl
  bootstrap::log "installing uv in the user-local tool directory"
  curl -LsSf "$(bootstrap::uv_install_url)" | sh >&2

  uv_bin="$(bootstrap::uv_bin_path || true)"
  [[ -n "$uv_bin" ]] || bootstrap::die "uv installation completed but no executable was found"
  printf '%s\n' "$uv_bin"
}

bootstrap::install_uv_python() {
  local uv_bin="$1"
  local python_version="$2"
  "$uv_bin" python install "$python_version" >&2
}

bootstrap::create_uv_venv() {
  local uv_bin="$1"
  local python_version="$2"
  local venv_dir="$3"
  "$uv_bin" venv --python "$python_version" "$venv_dir" >&2
}

bootstrap::install_locked_backend_deps() {
  local uv_bin="$1"
  local python_bin="$2"
  local requirements_file="$3"
  "$uv_bin" pip install --python "$python_bin" -r "$requirements_file" >&2
}

bootstrap::python_minor_version() {
  local python_bin="$1"
  "$python_bin" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'
}

bootstrap::python_matches_minor() {
  local python_bin="$1"
  local expected_minor="$2"
  [[ "$(bootstrap::python_minor_version "$python_bin" 2>/dev/null || true)" == "$expected_minor" ]]
}

bootstrap::python_has_module() {
  local python_bin="$1"
  local module_name="$2"
  "$python_bin" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec(\"$module_name\") else 1)" \
    >/dev/null 2>&1
}

bootstrap::node_version() {
  node -p 'process.versions.node'
}

bootstrap::node_version_at_least() {
  local minimum_version="$1"
  node - "$minimum_version" <<'NODE'
const minimum = process.argv[2];
const current = process.versions.node;

function parse(version) {
  return version.split(".").map((value) => Number.parseInt(value, 10) || 0);
}

const [currentMajor, currentMinor, currentPatch] = parse(current);
const [minimumMajor, minimumMinor, minimumPatch] = parse(minimum);

const isSatisfied =
  currentMajor > minimumMajor ||
  (currentMajor === minimumMajor &&
    (currentMinor > minimumMinor ||
      (currentMinor === minimumMinor && currentPatch >= minimumPatch)));

process.exit(isSatisfied ? 0 : 1);
NODE
}

bootstrap::print_node_install_help() {
  local os_name="$1"
  local minimum_version="$2"

  case "$os_name" in
    Darwin)
      cat >&2 <<EOF
Node.js >= ${minimum_version} and npm are required.
Install or update them on macOS with:
  /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "\$(/opt/homebrew/bin/brew shellenv)"
  brew install node@20
EOF
      ;;
    Linux)
      cat >&2 <<EOF
Node.js >= ${minimum_version} and npm are required.
Install or update them on Ubuntu/Debian with:
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
EOF
      ;;
    *)
      cat >&2 <<EOF
Node.js >= ${minimum_version} and npm are required.
Install them with your platform package manager and rerun this script.
EOF
      ;;
  esac
}

bootstrap::model_installed() {
  local python_bin="$1"
  local model_name="$2"
  "$python_bin" -c "import dacy; dacy.load('$model_name')" >/dev/null 2>&1
}

bootstrap::download_model_wheel() {
  local target_dir="$1"
  local model_url="$2"
  local model_file="$3"
  local tmp_wheel="$target_dir/.tmp-$model_file"
  local final_wheel="$target_dir/$model_file"

  bootstrap::require_cmd curl
  curl -L -o "$tmp_wheel" "$model_url" >&2
  mv "$tmp_wheel" "$final_wheel"
  printf '%s\n' "$final_wheel"
}

bootstrap::ensure_model_installed() {
  local uv_bin="$1"
  local python_bin="$2"
  local target_dir="$3"
  local model_name="$4"
  local model_url="$5"
  local model_file="$6"

  if bootstrap::model_installed "$python_bin" "$model_name"; then
    return 0
  fi

  bootstrap::log "installing NLP model $model_name"
  local wheel_path
  wheel_path="$(bootstrap::download_model_wheel "$target_dir" "$model_url" "$model_file")"
  "$uv_bin" pip install --python "$python_bin" --no-deps "$wheel_path" >&2
  bootstrap::model_installed "$python_bin" "$model_name" || bootstrap::die "failed to validate NLP model $model_name"
}
