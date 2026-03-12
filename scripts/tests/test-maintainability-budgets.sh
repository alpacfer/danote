#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
CHECKER="$ROOT_DIR/scripts/check-maintainability-budgets.sh"

run_checker_expect_pass() {
  local test_root="$1"
  MAINTAINABILITY_ROOT_DIR="$test_root" bash "$CHECKER" >/tmp/maintainability-pass.log
}

run_checker_expect_fail() {
  local test_root="$1"
  if MAINTAINABILITY_ROOT_DIR="$test_root" bash "$CHECKER" >/tmp/maintainability-fail.log 2>&1; then
    echo "expected checker to fail but it passed"
    cat /tmp/maintainability-fail.log
    exit 1
  fi
}

build_scaffold() {
  local test_root="$1"

  mkdir -p "$test_root/frontend/src/components/ui/vendor"
  mkdir -p "$test_root/frontend/src/app/hooks/app/controller"
  mkdir -p "$test_root/frontend/src/app/sections"

  mkdir -p "$test_root/backend/app/services/use_cases"
  mkdir -p "$test_root/backend/app/services"
  mkdir -p "$test_root/backend/app/db/repositories"
  mkdir -p "$test_root/backend/app/api/routes"
  mkdir -p "$test_root/backend/app/bootstrap"
  mkdir -p "$test_root/backend/app/core"

  cat > "$test_root/frontend/src/app/hooks/app/controller/index.ts" <<'SRC'
export const appController = () => "ok"
SRC

  cat > "$test_root/frontend/src/app/sections/index.tsx" <<'SRC'
export const Section = () => null
SRC

  cat > "$test_root/backend/app/api/routes/health.py" <<'SRC'
from fastapi import APIRouter

router = APIRouter()
SRC

  cat > "$test_root/backend/app/bootstrap/bootstrap.py" <<'SRC'
def bootstrap() -> None:
    return None
SRC

  cat > "$test_root/backend/app/core/config.py" <<'SRC'
class Config:
    debug = False
SRC
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# Case 1: oversized allowlisted vendor file should pass.
case_allowlisted="$tmpdir/allowlisted"
build_scaffold "$case_allowlisted"
python - <<'PY' "$case_allowlisted/frontend/src/components/ui/vendor/sidebar.tsx"
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text("\n".join(["export const Sidebar = () => null"] * 600) + "\n", encoding="utf-8")
PY
run_checker_expect_pass "$case_allowlisted"

# Case 2: oversized backend service should fail.
case_oversized="$tmpdir/oversized"
build_scaffold "$case_oversized"
python - <<'PY' "$case_oversized/backend/app/services/too_large_service.py"
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text("\n".join(["def ping():", "    return 1"] * 301) + "\n", encoding="utf-8")
PY
run_checker_expect_fail "$case_oversized"

echo "maintainability budget checker fixture tests passed"
