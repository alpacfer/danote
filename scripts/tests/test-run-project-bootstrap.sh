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

# Case 6: runtime config uses one canonical frontend port and includes it in CORS.
unset BACKEND_HOST BACKEND_PORT FRONTEND_HOST FRONTEND_PORT VITE_BACKEND_URL DANOTE_HOST DANOTE_PORT DANOTE_CORS_ORIGINS
configure_runtime
[[ "$BACKEND_HOST" == "127.0.0.1" ]]
[[ "$BACKEND_PORT" == "8000" ]]
[[ "$FRONTEND_HOST" == "127.0.0.1" ]]
[[ "$FRONTEND_PORT" == "5173" ]]
[[ "$VITE_BACKEND_URL" == "http://127.0.0.1:8000" ]]
[[ "$DANOTE_HOST" == "127.0.0.1" ]]
[[ "$DANOTE_PORT" == "8000" ]]
[[ "$DANOTE_CORS_ORIGINS" == *"http://127.0.0.1:5173"* ]]
[[ "$DANOTE_CORS_ORIGINS" == *"http://localhost:5173"* ]]

# Case 7: dotenv loading is safe, ordered, and does not source shell.
cat > "$ROOT_DIR/.env" <<'ENV'
# base values
DANOTE_TEST_BASE=base
DANOTE_TEST_OVERRIDE=from-env
DANOTE_TEST_QUOTED="quoted value"
ENV
cat > "$ROOT_DIR/.env.local" <<'ENV'

DANOTE_TEST_OVERRIDE=from-local
DANOTE_TEST_SINGLE_QUOTED='single quoted'
ENV
load_env_files >/dev/null
[[ "$DANOTE_TEST_BASE" == "base" ]]
[[ "$DANOTE_TEST_OVERRIDE" == "from-local" ]]
[[ "$DANOTE_TEST_QUOTED" == "quoted value" ]]
[[ "$DANOTE_TEST_SINGLE_QUOTED" == "single quoted" ]]

# Case 8: malformed dotenv lines report file and line.
bad_env_root="$tmpdir/bad-env-repo"
mkdir -p "$bad_env_root"
cat > "$bad_env_root/.env.local" <<'ENV'
DANOTE_OK=1
not an assignment
ENV
bad_env_log="$tmpdir/bad-env.log"
if bash -c "source '$RUN_PROJECT'; ROOT_DIR='$bad_env_root'; load_env_files" >"$bad_env_log" 2>&1; then
  echo "expected malformed env file to fail"
  exit 1
fi
grep -q ".env.local:2: invalid env assignment" "$bad_env_log"

# Case 9: unreplaced angle-bracket placeholders fail before startup.
placeholder_env_root="$tmpdir/placeholder-env-repo"
mkdir -p "$placeholder_env_root"
cat > "$placeholder_env_root/.env.local" <<'ENV'
DANOTE_KEY_ENCRYPTION_SECRET=<output of: openssl rand -base64 32>
ENV
placeholder_env_log="$tmpdir/placeholder-env.log"
if bash -c "source '$RUN_PROJECT'; ROOT_DIR='$placeholder_env_root'; load_env_files" >"$placeholder_env_log" 2>&1; then
  echo "expected placeholder env file to fail"
  exit 1
fi
grep -q "replace placeholder value for DANOTE_KEY_ENCRYPTION_SECRET" "$placeholder_env_log"

# Case 10: a healthy existing backend is reused instead of starting another process.
backend_is_healthy() { return 0; }
port_is_listening() { return 1; }
BACKEND_PID="sentinel"
start_backend
[[ -z "$BACKEND_PID" ]]

# Case 11: frontend startup uses strictPort so Vite cannot silently hop ports.
npm_run_log="$tmpdir/npm-run.log"
frontend_is_reachable() { return 1; }
port_is_listening() { return 1; }
fake_bin="$tmpdir/bin"
mkdir -p "$fake_bin"
cat > "$fake_bin/npm" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$*" > "$npm_run_log"
sleep 10
STUB
chmod +x "$fake_bin/npm"
PATH="$fake_bin:$PATH"
start_frontend
for _ in {1..20}; do
  [[ -f "$npm_run_log" ]] && break
  sleep 0.1
done
kill "$FRONTEND_PID" 2>/dev/null || true
wait "$FRONTEND_PID" 2>/dev/null || true
grep -q -- "--strictPort" "$npm_run_log"

echo "run-project bootstrap tests passed"
