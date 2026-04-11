@AGENTS.md

# CLAUDE.md

Claude Code guidance for danote. Shared agent policies in AGENTS.md (imported above).

## Commands

All from repo root.

```bash
make setup              # Install backend venv + frontend deps
make lint               # ESLint + compileall/ruff
make maintainability-check  # File size budgets
make test               # Backend unit + frontend tests
make test-backend-medium    # Backend integration
make test-backend-slow      # Regression fixtures
make docs-smoke         # Verify commands work
make dev                # Start backend + frontend
```

Single file:
```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/test_some_file.py
cd frontend && npx vitest run src/path/to/file.test.ts
```

## Architecture

### Backend

Entry: `app/main.py` → `create_app()` factory. Config: `DANOTE_*` env vars.
Layers: routes → schemas → use-cases → domain services → NLP adapters → DB.

### Frontend

React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui.

- App shell: `src/App.tsx` via `useAppController`
- Sections: `src/app/sections/` — Playground, Notes, Wordbank, Sentencebank, Developer
- Hooks: `src/app/hooks/` — by domain folder
- Chrome: `src/app/chrome/` — sidebar, breadcrumb, shell UI
- UI primitives: `src/components/ui/` — shadcn

Path alias: `@/*` → `./src/*`.

### CI (`.github/workflows/quality.yml`)

1. **fast-quality**: lint → maintainability-check → test → docs-smoke
2. **medium-backend-integration**: backend medium tests

Python 3.10, Node 22.

## Subagents

| Agent | When |
|-------|------|
| `test-writer` | Tests, coverage gaps, post-impl |
| `docs-updater` | Pre-PR docs audit, after API/schema/workflow change |
| `danish-linguist` | NLP pipeline, token classification, COR lexicon, translation |

### Commands (`.claude/commands/`)

| Command | Use |
|---------|-----|
| `/researcher` | Deep codebase + external docs research |
| `/api-change` | Schema-first API change workflow |

### Built-in agents

Explore (quick nav), Plan (impl strategy), general-purpose (multi-step).

## Hooks (`.claude/hooks/`)

All warn-only (exit 0) except `protect-env-files.sh` (exit 2 blocks).

| Hook | Trigger | Effect |
|------|---------|--------|
| `post-edit-lint.sh` | Edit/Write `*.py` | ruff warnings |
| `post-edit-lint.sh` | Edit/Write `*.ts`/`*.tsx` | maintainability-check warnings |
| `pre-commit-check.sh` | `git commit` via Bash | `make lint && make test` warnings |
| `protect-env-files.sh` | Edit/Write `.env*` | **Blocks** edit (exit 2) |
| `session-context.sh` | SessionStart (compact) | Re-injects context |
| `notify.sh` | Notification | Desktop alert (async) |

## Rules (`.claude/rules/`)

| File | Paths | Content |
|------|-------|---------|
| `testing.md` | `backend/tests/**`, `frontend/src/test/**` | pytest/vitest patterns |
| `api-design.md` | `backend/app/api/**`, `services/use_cases/**` | Schema-first, thin routes |
| `frontend.md` | `frontend/src/**/*.{ts,tsx}` | shadcn-first, hook boundaries, size limits |

## Context Management

Read priority: (1) changed files + imports, (2) tests, (3) schemas, (4) use-cases, (5) domain services.

Reduce pressure: use Explore agent for broad searches; read hook before component; read use-case before route; read hook + section + tests as unit per domain.
