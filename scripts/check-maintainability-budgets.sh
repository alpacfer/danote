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

echo "[maintainability] warnings=$warn_count failures=$fail_count"

if (( fail_count > 0 )); then
  echo "[maintainability] budget check failed"
  exit 1
fi

echo "[maintainability] budget check passed"
