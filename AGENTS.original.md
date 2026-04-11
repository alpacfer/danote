# AGENTS.md

This file gives AI agents fast, deterministic context for working in this repository.

## Mission

danote is a Danish-first language-learning notes app with:
- `frontend/`: React + Vite UI
- `backend/`: FastAPI + SQLite + NLP/typo pipeline

## Verification workflow (run from repo root)

- Default: run the smallest relevant verification set that covers the changed boundary.
- Escalate to the full suite only when the change is broad, risky, cross-cutting, or hard to isolate:
  1. `make lint`
  2. `make test`
  3. `make docs-smoke`
- If you change backend orchestration or API schemas, additionally run:
  `bash ./scripts/pytest-backend.sh -q tests/use_cases`
- Typical targeted examples:
  - frontend-only/UI change: run the nearest affected Vitest file(s)
  - backend-only behavior change: run the nearest affected pytest module(s)
  - docs/workflow-only change: run `make docs-smoke`

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
- Prefer the smallest verification set that proves the changed behavior.
- Update docs when command or workflow behavior changes.
- For frontend/UI changes, default to using existing shadcn/ui components before building custom UI primitives.
- For frontend/UI changes, first review the relevant official shadcn/ui component docs and assess the best-fit primitive before implementing.
- Record the chosen shadcn primitive and why nearby alternatives were rejected when that decision affects the UI structure or interaction model.
- When adding a new shadcn component, always use the official CLI command with default values:
  `npx shadcn@latest add <component>`.
  Do not handcraft component source or use custom generator settings unless explicitly requested.
- When a required shadcn component is not present, install it first and use the generated component mostly as-is.
  Prefer composing around the generated API and styling via props/class names instead of rewriting the component internals unless explicitly requested.
- Frontend UI workflow should be: review repo docs/patterns, review shadcn docs, choose/install the primitive, compose from shadcn primitives, then update tests and docs in the same change.

## Documentation Sync Rule (mandatory)

- Before implementing any code/config/schema/workflow change, agents must first locate and read the related documentation in `README.md` and/or `docs/`.
- Documentation lookup is a required pre-implementation step (not optional) and should be reflected in the agent's execution notes.
- Any code/config/API/schema/workflow change must include documentation updates in the same PR.
- If no documentation files were changed, the PR must explicitly include a clear "No documentation impact" justification.
- After implementation, agents must update all impacted docs before finishing (or include an explicit, justified "No documentation impact" note).
- API route or API schema changes must update `docs/api-contract.md`.
- Command/setup/workflow changes must update `README.md` and relevant documentation under `docs/`.
- Version/dependency/runtime changes must update `docs/versions.md`.
- Completion checklists must include an explicit documentation parity verification checkbox.

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

- Run targeted checks that directly cover the changed files/behavior by default.
- Run the full suite (`make lint`, `make test`, `make docs-smoke`) for broad or high-blast-radius changes, including refactors across multiple modules, workflow/build/dependency changes, and changes whose impact cannot be cleanly isolated.
- If behavior was moved across files, ensure tests still cover the moved behavior.
- In the final summary, call out major extracted modules so future contributors can find ownership quickly.

## Self-verification checklist before finishing

- [ ] Related documentation reviewed before implementation (`README.md` and/or `docs/*`)
- [ ] Relevant verification for the changed boundary was executed and passes
- [ ] If the change is broad/high-risk: `make lint`, `make test`, and `make docs-smoke` pass
- [ ] If backend orchestration changed: `tests/use_cases` passes
- [ ] Documentation parity verified (docs updated or PR includes explicit "No documentation impact" justification)
- [ ] No unstaged/untracked scratch files remain

## Quick file lookup

- Backend app entry: `backend/app/main.py`
- API router root: `backend/app/api/router.py`
- Frontend app entry: `frontend/src/App.tsx`
- End-to-end script: `scripts/e2e-regression.sh`
- Docs smoke checks: `scripts/docs-smoke.sh`
