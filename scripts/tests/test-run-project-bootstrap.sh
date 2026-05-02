#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_PROJECT="$ROOT_DIR/scripts/run-project.sh"

# shellcheck source=../run-project.sh
source "$RUN_PROJECT"

make_stub_python() {
  local target="$1"
  cat > "$target" <<'STUB'
#!/usr/bin/env bash
case "${2:-}" in
  *"sys.version_info[0]"*)
    printf '%s\n' "${STUB_PYTHON_VERSION:-3.12}"
    ;;
  *'find_spec("uvicorn")'*)
    [[ "${STUB_HAS_UVICORN:-0}" == "1" ]]
    ;;
  *)
    exit 0
    ;;
esac
STUB
  chmod +x "$target"
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

PLATFORM_OS="Darwin"
PYTHON_VERSION="3.11"
ROOT_DIR="$tmpdir/repo"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
mkdir -p "$BACKEND_DIR" "$FRONTEND_DIR"

# Case 1: missing backend venv should be detected.
[[ "$(backend_env_reason)" == "missing backend interpreter" ]]

# Case 2: stale backend venv missing uvicorn should be detected.
mkdir -p "$BACKEND_DIR/.venv/bin"
make_stub_python "$BACKEND_DIR/.venv/bin/python"
export STUB_PYTHON_VERSION="3.11"
export STUB_HAS_UVICORN="0"
[[ "$(backend_env_reason)" == "backend venv is missing uvicorn" ]]

# Case 3: wrong Python version should trigger venv recreation logic.
recreate_calls=0
bootstrap::ensure_uv() { printf '%s\n' "/tmp/fake-uv"; }
bootstrap::install_uv_python() { :; }
bootstrap::create_uv_venv() {
  recreate_calls=$((recreate_calls + 1))
  mkdir -p "$3/bin"
  make_stub_python "$3/bin/python"
}
bootstrap::install_locked_backend_deps() { :; }
export STUB_PYTHON_VERSION="3.9"
export STUB_HAS_UVICORN="1"
ensure_backend_env
[[ "$recreate_calls" -eq 1 ]]

# Case 4: unsupported OS should fail with a clear message.
unsupported_log="$tmpdir/unsupported.log"
if DANOTE_BOOTSTRAP_OS_OVERRIDE="FreeBSD" bash -c "source '$RUN_PROJECT'; assert_supported_platform" >"$unsupported_log" 2>&1; then
  echo "expected unsupported platform check to fail"
  exit 1
fi
grep -q "Supported platforms are macOS and Linux" "$unsupported_log"

# Case 5: missing node/npm should print install guidance.
missing_node_log="$tmpdir/missing-node.log"
minimal_path="/usr/bin:/bin"
if PATH="$minimal_path" /bin/bash -c "source '$RUN_PROJECT'; PLATFORM_OS='Darwin'; NODE_MIN_VERSION='20.19.0'; assert_frontend_runtime" >"$missing_node_log" 2>&1; then
  echo "expected frontend runtime check to fail"
  exit 1
fi
grep -q "brew install node@20" "$missing_node_log"

echo "run-project bootstrap tests passed"
