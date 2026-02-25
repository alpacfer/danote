# Repository Analysis: Current Problems, Issues, and Bugs

Date: 2026-02-25

## Scope

This analysis reviewed both backend and frontend code paths and ran available automated checks.

## Findings

### 1) Frontend lint fails due to React purity violation in `SidebarMenuSkeleton`

- **Severity:** High (CI/static-quality gate fails)
- **Evidence:** `Math.random()` is called during render logic via `useMemo`, which violates React purity constraints and is flagged by ESLint.
- **Code location:** `frontend/src/components/ui/sidebar.tsx` lines 609-612.
- **Impact:** Non-deterministic rendering behavior and guaranteed lint failure.
- **Recommendation:** Replace random width generation with deterministic props/data or precomputed values outside render.

### 2) Frontend lint fails due to Fast Refresh export rule violations in shared UI files

- **Severity:** Medium (tooling/quality gate failure)
- **Evidence:** ESLint `react-refresh/only-export-components` errors are raised for files that export helper constants/functions alongside components.
- **Code location examples:**
  - `frontend/src/components/ui/button.tsx` line 64 (`export { Button, buttonVariants }`)
  - Similar violations are reported in `badge.tsx`, `navigation-menu.tsx`, `sidebar.tsx`, and `tabs.tsx`.
- **Impact:** `npm run lint` fails, preventing a green quality check baseline.
- **Recommendation:** Move non-component exports (e.g., variant builders/constants) into separate files or relax the rule for generated shadcn-style components.

### 3) Root README uses machine-specific absolute paths in multiple commands

- **Severity:** Medium (developer onboarding/documentation bug)
- **Evidence:** The runbook includes absolute paths such as `/home/alejandro/Documents/github/danote/danote`.
- **Code locations:** `README.md` lines 18, 91, and 105.
- **Impact:** Commands are not portable and fail for most users/environments.
- **Recommendation:** Replace with relative instructions (e.g., `cd <repo-root>`).

### 4) Backend test command in docs is incomplete for current import layout

- **Severity:** Medium (developer workflow breakage)
- **Evidence:** `backend/README.md` recommends `pytest`, but test collection fails in a clean shell without `PYTHONPATH=.` due to `ModuleNotFoundError: No module named 'app'`.
- **Code location:** `backend/README.md` lines 113-117.
- **Impact:** New contributors can fail immediately when following documented steps.
- **Recommendation:** Update docs to use `PYTHONPATH=. pytest` (or package/install backend so `app` resolves without PYTHONPATH).

## Commands Executed

- `cd backend && PYTHONPATH=. pytest -q tests/test_typo_engine_unit.py tests/test_token_classifier_unit.py tests/test_token_filter_unit.py` → passed.
- `cd frontend && npm test -- --run` → passed.
- `cd frontend && npm run lint` → failed with six ESLint errors (purity + fast-refresh export rule).
- `cd backend && PYTHONPATH=. pytest -q` → blocked by missing `httpx` in the current environment.

## Notes

A full backend integration test run in this execution environment was limited by dependency resolution/network constraints for `httpx`; unit-level backend checks and frontend tests were still executed successfully.
