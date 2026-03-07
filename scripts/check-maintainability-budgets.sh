#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

warn_count=0
fail_count=0

echo "[maintainability] scanning non-test file budgets"

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  lines=$(wc -l < "$file")
  if (( lines > 450 )); then
    echo "[FAIL] ts/tsx hard limit >450: $file ($lines)"
    fail_count=$((fail_count + 1))
  elif (( lines > 300 )); then
    echo "[WARN] ts/tsx soft limit >300: $file ($lines)"
    warn_count=$((warn_count + 1))
  fi
done < <(rg --files frontend/src | rg -v '(/test/|\.test\.|\.spec\.|/__tests__/|components/ui/vendor/sidebar\.tsx$)' | rg '\.(ts|tsx)$')

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  lines=$(wc -l < "$file")
  if (( lines > 200 )); then
    echo "[WARN] tsx component target >200: $file ($lines)"
    warn_count=$((warn_count + 1))
  fi
done < <(rg --files frontend/src | rg -v '(/test/|\.test\.|\.spec\.|/__tests__/|components/ui/vendor/sidebar\.tsx$)' | rg '\.tsx$')

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  lines=$(wc -l < "$file")
  if (( lines > 700 )); then
    echo "[FAIL] backend use-case hard limit >700: $file ($lines)"
    fail_count=$((fail_count + 1))
  elif (( lines > 350 )); then
    echo "[WARN] backend use-case soft limit >350: $file ($lines)"
    warn_count=$((warn_count + 1))
  fi
done < <(rg --files backend/app/services/use_cases | rg -v '(/tests?/|\.test\.|\.spec\.|/__tests__/)' | rg '\.py$')

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  lines=$(wc -l < "$file")
  if (( lines > 350 )); then
    echo "[FAIL] backend app boundary hard limit >350: $file ($lines)"
    fail_count=$((fail_count + 1))
  elif (( lines > 250 )); then
    echo "[WARN] backend app boundary soft limit >250: $file ($lines)"
    warn_count=$((warn_count + 1))
  fi
done < <(rg --files backend/app/api/routes backend/app/bootstrap backend/app/core | rg '\.py$')

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
