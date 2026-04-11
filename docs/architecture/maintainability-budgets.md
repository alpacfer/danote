# Maintainability budget thresholds

Budgets enforced by `scripts/check-maintainability-budgets.sh`, run via `make maintainability-check`.

## Enforced file-size budgets

- Frontend prod `*.ts`/`*.tsx` (non-test):
  - Warn above **300** lines.
  - Fail above **450** lines.
- Frontend `*.tsx` component target (non-test):
  - Warn above **200** lines.
- Backend use-cases `backend/app/services/use_cases/**/*.py`:
  - Warn above **350** lines.
  - Fail above **700** lines.
- Backend domain services `backend/app/services/**/*.py` (excl. `use_cases/`):
  - Warn above **300** lines.
  - Fail above **600** lines.
- Backend repositories `backend/app/db/repositories/**/*.py`:
  - Warn above **300** lines.
  - Fail above **800** lines.
- Backend app-boundary files in `backend/app/api/routes`, `backend/app/bootstrap`, `backend/app/core`:
  - Warn above **250** lines.
  - Fail above **350** lines.
- Frontend app-controller hooks in `frontend/src/app/hooks/app/controller`:
  - Fail above **220** lines.

Checker also enforces architecture boundaries (route import restrictions, frontend section transport restrictions).

## Exemption allowlist policy

Only generated/vendor files may bypass budgets.

Current allowlist:
- `frontend/src/components/ui/vendor/sidebar.tsx`

### How to request a new exemption

1. Confirm file is generated/vendored — not hand-written app logic.
2. Add exact relative path to allowlist in `scripts/check-maintainability-budgets.sh`.
3. Same PR: document why exemption needed + who owns upstream updates.
4. Add/update checker fixture test proving exemption stays intentional.

No exemptions for product code — refactor instead.