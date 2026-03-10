# AGENTS.md

This file gives AI agents fast, deterministic context for working in this repository.

## Mission

danote is a Danish-first language-learning notes app with:
- `frontend/`: React + Vite UI
- `backend/`: FastAPI + SQLite + NLP/typo pipeline

## Canonical workflow (run from repo root)

1. `make lint`
2. `make test`
3. `make docs-smoke`

If you change backend orchestration or API schemas, additionally run:

4. `bash ./scripts/pytest-backend.sh -q tests/use_cases`

## Architecture map

- HTTP transport only: `backend/app/api/routes/`
- API DTOs (versioned): `backend/app/api/schemas/v1/`
- Application/use-case layer: `backend/app/services/use_cases/`
- Domain services: `backend/app/services/`
- NLP adapters: `backend/app/nlp/`
- DB/migrations: `backend/app/db/`

## Change policy for agents

- Keep route handlers thin; place orchestration in `services/use_cases/`.
- Add/modify request-response models in `api/schemas/v1/` first; route files should import from schemas.
- Prefer adding/expanding tests rather than changing expectations silently.
- Update docs when command or workflow behavior changes.
- For frontend/UI changes, default to using existing shadcn/ui components before building custom UI primitives.
- When adding a new shadcn component, always use the official CLI command with default values:
  `npx shadcn@latest add <component>`.
  Do not handcraft component source or use custom generator settings unless explicitly requested.
- When a required shadcn component is not present, install it first and use the generated component mostly as-is.
  Prefer composing around the generated API and styling via props/class names instead of rewriting the component internals unless explicitly requested.

## Maintainability guardrails (mandatory)

- Build for long-term maintainability over short-term speed. Avoid "god files" and mixed responsibilities.
- Follow single-responsibility by default:
  - UI components render and handle UI events.
  - Data fetching, orchestration, and side effects live in hooks/services.
  - Shared pure logic lives in focused utility modules.
- Do not add new feature logic to already-large files without extracting first.

### File size and complexity limits

- Production `*.ts` / `*.tsx` files:
  - Target: <= 300 lines.
  - Soft limit: 300-450 lines (allowed only with clear reason).
  - Hard limit: > 450 lines requires refactor/split in the same change.
- React components:
  - Target: <= 200 lines and one main concern.
- Custom hooks:
  - Target: <= 220 lines and one workflow/domain concern.
- Functions:
  - Target: <= 60 lines.
  - If branching/nesting gets deep, split into named helpers.
- Test files:
  - Target: <= 1200 lines.
  - If larger, extract builders/fixtures/helpers into `test` helper modules.

### Required refactor triggers

- If you touch a file > 450 lines and add non-trivial logic, include a split/refactor in the same task.
- If a component starts handling 3+ domain workflows (for example notes + popovers + wordbank), extract orchestration into dedicated hooks/modules.
- If prop lists become unwieldy (roughly 15+), group related props into typed objects or split component boundaries.
- If a file name becomes generic (`utils.ts`, `helpers.ts`) and grows, split by domain with explicit names.

### Organization and boundaries

- Prefer domain folders over flat structure (for example `hooks/playground/*`, `hooks/wordbank/*`).
- Keep app composition files thin (`App.tsx` should orchestrate and compose, not own detailed workflow logic).
- Keep backend layering strict:
  - routes -> schemas -> use-cases -> domain services.
  - Do not move orchestration into route handlers.
- Keep module APIs explicit; export stable public hooks/components from index barrels when useful.

### Type safety and readability

- Avoid `any`; prefer explicit types at module boundaries.
- Keep state shapes typed and named by domain.
- Use small, intention-revealing function names.
- Add brief comments only where logic is non-obvious; do not narrate obvious code.

### Verification before finishing

- Run full checks (`make lint`, `make test`, `make docs-smoke`) after refactors, not only after feature changes.
- If behavior was moved across files, ensure tests still cover the moved behavior.
- In the final summary, call out major extracted modules so future contributors can find ownership quickly.

## Self-verification checklist before finishing

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] `make docs-smoke` passes
- [ ] If backend orchestration changed: `tests/use_cases` passes
- [ ] No unstaged/untracked scratch files remain

## Quick file lookup

- Backend app entry: `backend/app/main.py`
- API router root: `backend/app/api/router.py`
- Frontend app entry: `frontend/src/App.tsx`
- End-to-end script: `scripts/e2e-regression.sh`
- Docs smoke checks: `scripts/docs-smoke.sh`
