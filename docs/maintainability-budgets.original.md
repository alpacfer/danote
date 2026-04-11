# Maintainability budget thresholds

This document defines the budget thresholds enforced by `scripts/check-maintainability-budgets.sh` and run by `make maintainability-check`.

## Enforced file-size budgets

- Frontend production `*.ts`/`*.tsx` (non-test):
  - Warn above **300** lines.
  - Fail above **450** lines.
- Frontend `*.tsx` component target (non-test):
  - Warn above **200** lines.
- Backend use-cases `backend/app/services/use_cases/**/*.py`:
  - Warn above **350** lines.
  - Fail above **700** lines.
- Backend domain services `backend/app/services/**/*.py` (excluding `use_cases/`):
  - Warn above **300** lines.
  - Fail above **600** lines.
- Backend repositories `backend/app/db/repositories/**/*.py`:
  - Warn above **300** lines.
  - Fail above **800** lines.
- Backend app-boundary files in `backend/app/api/routes`, `backend/app/bootstrap`, and `backend/app/core`:
  - Warn above **250** lines.
  - Fail above **350** lines.
- Frontend app-controller hooks in `frontend/src/app/hooks/app/controller`:
  - Fail above **220** lines.

The checker also enforces architecture boundaries (for example, route import restrictions and frontend section transport restrictions).

## Exemption allowlist policy

Only intentional generated/vendor files are allowed to bypass budgets.

Current allowlist:
- `frontend/src/components/ui/vendor/sidebar.tsx`

### How to request a new exemption

1. Confirm the file is generated or vendored and should not be maintained as hand-written application logic.
2. Add the exact relative path to the allowlist in `scripts/check-maintainability-budgets.sh`.
3. In the same PR, document why the exemption is needed and who owns upstream updates.
4. Add or update a checker fixture test proving the exemption behavior remains intentional.

Do not add exemptions for regular product code; refactor instead.
