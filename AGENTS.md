# AGENTS.md

AI agent context for danote: Danish-first language-learning app. `frontend/` React+Vite, `backend/` FastAPI+SQLite+NLP.

## Verification

- Run smallest set covering changed boundary. Escalate to full suite for broad/risky changes:
  1. `make lint`
  2. `make test`
  3. `make docs-smoke`
- Backend orchestration/schema changes: `bash ./scripts/pytest-backend.sh -q tests/use_cases`
- Targeted: frontend-only → nearest Vitest; backend-only → nearest pytest; docs-only → `make docs-smoke`

## Architecture map

- Routes: `backend/app/api/routes/`
- DTOs: `backend/app/api/schemas/v1/`
- Use-cases: `backend/app/services/use_cases/`
- Domain services: `backend/app/services/`
- NLP: `backend/app/nlp/`
- DB: `backend/app/db/`

## Change policy

- Routes thin; orchestration in `services/use_cases/`.
- DTOs in `api/schemas/v1/` first; routes import from schemas.
- Prefer adding/expanding tests over changing expectations silently.
- Smallest verification set that proves changed behavior.
- Update docs when command/workflow behavior changes.
- Frontend: existing shadcn/ui before custom UI. Review shadcn docs first.
- Install shadcn: `npx shadcn@latest add <component>` with defaults. Don't handcraft.
- Frontend workflow: review docs → review shadcn docs → install primitive → compose → test → doc.

## Documentation Sync (mandatory)

- Read related docs (`README.md`, `docs/`) before implementing.
- Any code/config/API/schema change → update docs in same PR.
- No doc changes → PR must include "No documentation impact" justification.
- API route/schema changes → `docs/api-contract.md`.
- Command/setup changes → `README.md` + `docs/`.
- Version/dep changes → `docs/versions.md`.
- Completion checklists → explicit docs parity checkbox.

## Maintainability guardrails

- UI components render + handle UI events. Data fetching/ orchestration/ side effects in hooks/services. Shared pure logic in utility modules.
- Don't add feature logic to large files without extracting first.

### File size limits

- `*.ts`/`*.tsx`: target ≤300, soft ≤450, hard >450 → refactor.
- React components: target ≤200 lines, one concern.
- Custom hooks: target ≤220 lines, one workflow.
- Functions: target ≤60 lines.
- Test files: target ≤1200 lines.

### Required refactor triggers

- Touch file >450 lines + add non-trivial logic → split in same change.
- Component handles 3+ domain workflows → extract hooks.
- Prop list ≥15 → group into typed objects or split.
- Generic file (`utils.ts`) grows → split by domain.

### Organization

- Domain folders over flat (`hooks/playground/*`, `hooks/wordbank/*`).
- `App.tsx` composes, doesn't own workflow logic.
- Backend layering strict: routes → schemas → use-cases → domain services.
- Module APIs explicit; export stable hooks/components from index barrels.

### Type safety

- Avoid `any`; explicit types at boundaries.
- State shapes typed + named by domain.
- Small intention-revealing names.
- Comments only where non-obvious.

## Verification before finishing

- Targeted checks covering changed files/behavior by default.
- Full suite for broad/high-risk changes (refactors, workflow/build/dep changes, unclear blast radius).
- If behavior moved → tests still cover moved behavior.
- Final summary: call out extracted modules.

## Self-verification checklist

- [ ] Docs reviewed before impl (`README.md` and/or `docs/*`)
- [ ] Verification for changed boundary executed + passes
- [ ] Broad changes: `make lint`, `make test`, `make docs-smoke` pass
- [ ] Backend orchestration changed: `tests/use_cases` passes
- [ ] Docs parity verified (updated or "No documentation impact")
- [ ] No unstaged/untracked scratch files

## Quick file lookup

- Backend entry: `backend/app/main.py`
- API router: `backend/app/api/router.py`
- Frontend entry: `frontend/src/App.tsx`
- E2E: `scripts/e2e-regression.sh`
- Docs smoke: `scripts/docs-smoke.sh`
