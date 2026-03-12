#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${MAINTAINABILITY_ROOT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT_DIR"

warn_count=0
fail_count=0

ALLOWLIST_REGEX='^(frontend/src/components/ui/vendor/sidebar\.tsx)$'

is_allowlisted() {
  local file="$1"
  [[ "$file" =~ $ALLOWLIST_REGEX ]]
}

scan_budget() {
  local label="$1"
  local soft_limit="$2"
  local hard_limit="$3"
  local warn_message="$4"
  local fail_message="$5"

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    if is_allowlisted "$file"; then
      continue
    fi

    local lines
    lines=$(wc -l < "$file")

    if (( lines > hard_limit )); then
      echo "[FAIL] $fail_message: $file ($lines)"
      fail_count=$((fail_count + 1))
    elif (( lines > soft_limit )); then
      echo "[WARN] $warn_message: $file ($lines)"
      warn_count=$((warn_count + 1))
    fi
  done
}

echo "[maintainability] scanning non-test file budgets"

scan_budget \
  "frontend ts/tsx" \
  300 \
  450 \
  "ts/tsx soft limit >300" \
  "ts/tsx hard limit >450" \
  < <(rg --files frontend/src | rg -v '(/test/|\.test\.|\.spec\.|/__tests__/)' | rg '\.(ts|tsx)$')

scan_budget \
  "frontend tsx components" \
  200 \
  999999 \
  "tsx component target >200" \
  "unused" \
  < <(rg --files frontend/src | rg -v '(/test/|\.test\.|\.spec\.|/__tests__/)' | rg '\.tsx$')

scan_budget \
  "backend use-cases" \
  350 \
  700 \
  "backend use-case soft limit >350" \
  "backend use-case hard limit >700" \
  < <(rg --files backend/app/services/use_cases | rg -v '(/tests?/|\.test\.|\.spec\.|/__tests__/)' | rg '\.py$')

scan_budget \
  "backend services" \
  300 \
  600 \
  "backend service soft limit >300" \
  "backend service hard limit >600" \
  < <(rg --files backend/app/services | rg -v '(/use_cases/|/tests?/|\.test\.|\.spec\.|/__tests__/)' | rg '\.py$')

scan_budget \
  "backend repositories" \
  300 \
  800 \
  "backend repository soft limit >300" \
  "backend repository hard limit >800" \
  < <(rg --files backend/app/db/repositories | rg -v '(/tests?/|\.test\.|\.spec\.|/__tests__/)' | rg '\.py$')

scan_budget \
  "backend app boundary" \
  250 \
  350 \
  "backend app boundary soft limit >250" \
  "backend app boundary hard limit >350" \
  < <(rg --files backend/app/api/routes backend/app/bootstrap backend/app/core | rg '\.py$')

echo "[maintainability] scanning architecture boundaries"

backend_route_violations="$(rg -n '^(from|import) app\.(db|nlp|services\.)' backend/app/api/routes --glob '*.py' | rg -v 'app\.services\.use_cases' || true)"
if [[ -n "$backend_route_violations" ]]; then
  echo "[FAIL] backend routes must stay transport-only and avoid direct db/nlp/provider imports:"
  echo "$backend_route_violations"
  fail_count=$((fail_count + 1))
fi

frontend_section_violations="$(rg -n '(@/app/core/api-client|@/app/core/api-runtime|\bfetch\()' frontend/src/app/sections --glob '*.{ts,tsx}' || true)"
if [[ -n "$frontend_section_violations" ]]; then
  echo "[FAIL] frontend sections must not call transport directly:"
  echo "$frontend_section_violations"
  fail_count=$((fail_count + 1))
fi

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  if is_allowlisted "$file"; then
    continue
  fi

  lines=$(wc -l < "$file")
  if (( lines > 220 )); then
    echo "[FAIL] app-controller orchestration hard limit >220: $file ($lines)"
    fail_count=$((fail_count + 1))
  fi
done < <(rg --files frontend/src/app/hooks/app/controller | rg '\.(ts|tsx)$')

echo "[maintainability] warnings=$warn_count failures=$fail_count"

if (( fail_count > 0 )); then
  echo "[maintainability] budget check failed"
  exit 1
fi

echo "[maintainability] budget check passed"
