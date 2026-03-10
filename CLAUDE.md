# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

danote is a Danish-first language-learning note-taking web app with a React/Vite frontend and a FastAPI/SQLite backend with NLP and typo-detection pipelines.

## Common Commands

All commands run from repo root unless noted.

```bash
make setup              # Install backend venv + frontend deps
make lint               # ESLint (frontend) + compileall/ruff (backend)
make maintainability-check  # File size budget guardrails
make test               # Backend unit tests + frontend tests (fast)
make test-backend-medium    # Backend integration tests (needs running backend deps)
make test-backend-slow      # Regression fixture tests (needs DaCy model)
make docs-smoke         # Verify documented commands still work
make dev                # Start backend + frontend together (scripts/run-project.sh)
```

Run a single backend test file:
```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/test_some_file.py
```

Run a single frontend test file:
```bash
cd frontend && npx vitest run src/path/to/file.test.ts
```

## Architecture

### Backend (`backend/`)

Strict layered architecture — routes must stay thin:

- **Routes** (`app/api/routes/`): HTTP transport only — validation, error mapping, delegation to use-cases
- **Schemas** (`app/api/schemas/v1/`): Versioned request/response DTOs. Routes import from here; never define models inline in routes
- **Use-cases** (`app/services/use_cases/`): Business orchestration layer (analyze, wordbank, sentencebank, developer)
- **Domain services** (`app/services/`): COR lexicon, translation (Azure), TTS (Azure Speech), typo engine, word verification (Gemini), token classifier
- **NLP adapters** (`app/nlp/`): spaCy/DaCy model wrappers
- **DB/migrations** (`app/db/`): SQLite with auto-migration on startup

Entry point: `app/main.py` → `create_app()` factory. Config via `DANOTE_*` env vars (loaded from `.env` / `.env.local`).

### Frontend (`frontend/`)

React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui components.

- **App shell** (`src/App.tsx`): Composes sidebar + section routing via `useAppController` hook
- **Sections** (`src/app/sections/`): Playground, Notes, Wordbank, Sentencebank, Developer — each a top-level view
- **Hooks** (`src/app/hooks/`): Domain-specific hooks organized by folder (app, playground, wordbank, etc.)
- **Chrome** (`src/app/chrome/`): Sidebar, breadcrumb, and shell UI
- **UI components** (`src/components/ui/`): shadcn components — add new ones via `npx shadcn@latest add <component>`

Path alias: `@/*` maps to `./src/*`.

### CI Pipeline (`.github/workflows/quality.yml`)

Two jobs:
1. **fast-quality**: lint → maintainability-check → test → docs-smoke
2. **medium-backend-integration**: backend medium tests (runs after fast-quality)

Python 3.10, Node 22.

## Key Conventions

### Edit Strategy

1. Update schemas in `api/schemas/v1/` first (if API shape changes)
2. Update use-case logic in `services/use_cases/`
3. Keep route changes minimal
4. Add tests nearest to the changed boundary

### File Size Limits (enforced by `make maintainability-check`)

- Production TS/TSX: target ≤300 lines, soft limit 300–450, hard limit >450 requires refactor
- React components: ≤200 lines, one main concern
- Custom hooks: ≤220 lines, one workflow/domain concern
- Functions: ≤60 lines

### Code Quality

- No `any` in TypeScript; use explicit types at module boundaries
- Keep `App.tsx` as a thin orchestrator — workflow logic belongs in hooks
- Prefer domain folders over flat structure (e.g. `hooks/playground/`, `hooks/wordbank/`)
- Backend: never put business logic in route handlers

### Verification Sequence

Run this before finishing any change:
```bash
make lint
make maintainability-check
make test
make docs-smoke
```

If backend orchestration or schemas changed, also run:
```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases
```
