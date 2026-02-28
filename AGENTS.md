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

4. `cd backend && PYTHONPATH=. pytest -q tests/test_use_cases_unit.py`

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
- When adding a new shadcn component, always use the official CLI command with default values:
  `npx shadcn@latest add <component>`.
  Do not handcraft component source or use custom generator settings unless explicitly requested.

## Self-verification checklist before finishing

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] `make docs-smoke` passes
- [ ] If backend orchestration changed: `tests/test_use_cases_unit.py` passes
- [ ] No unstaged/untracked scratch files remain

## Quick file lookup

- Backend app entry: `backend/app/main.py`
- API router root: `backend/app/api/router.py`
- Frontend app entry: `frontend/src/App.tsx`
- End-to-end script: `scripts/e2e-regression.sh`
- Docs smoke checks: `scripts/docs-smoke.sh`
