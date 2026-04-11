@AGENTS.md

# CLAUDE.md

Claude Code-specific guidance for danote. Shared agent policies are in AGENTS.md (imported above).

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
make dev                # Start backend + frontend together
```

Single file tests:
```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/test_some_file.py
cd frontend && npx vitest run src/path/to/file.test.ts
```

## Architecture Details

### Backend

Entry point: `app/main.py` → `create_app()` factory.
Config: `DANOTE_*` env vars (loaded from `.env` / `.env.local`).
Layering: routes → schemas → use-cases → domain services → NLP adapters → DB.

Domain services: COR lexicon, translation (Azure), TTS (Azure Speech), typo engine, word verification (Gemini), token classifier.

### Frontend

React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui.

- App shell: `src/App.tsx` composes sidebar + section routing via `useAppController`
- Sections: `src/app/sections/` — Playground, Notes, Wordbank, Sentencebank, Developer
- Hooks: `src/app/hooks/` — organized by domain folder
- Chrome: `src/app/chrome/` — sidebar, breadcrumb, shell UI
- UI primitives: `src/components/ui/` — shadcn (add via `npx shadcn@latest add <name>`)

Path alias: `@/*` → `./src/*`.

### CI Pipeline (`.github/workflows/quality.yml`)

1. **fast-quality**: lint → maintainability-check → test → docs-smoke
2. **medium-backend-integration**: backend medium tests (after fast-quality)

Python 3.10, Node 22.

## Subagents

### Project agents (`.claude/agents/`) — auto-dispatched by context

| Agent | Activates when |
|-------|---------------|
| `test-writer` | Writing tests, filling coverage gaps, post-implementation |
| `docs-updater` | Pre-PR docs audit, after any API/schema/workflow change |
| `danish-linguist` | NLP pipeline, token classification, COR lexicon, translation |

### Commands (`.claude/commands/`) — explicit invocation

| Command | Usage |
|---------|-------|
| `/researcher` | Deep codebase + external docs research |
| `/api-change` | Guided schema-first API change workflow |

### Built-in agents

| Agent | Use when |
|-------|----------|
| **Explore** | Quick codebase navigation, finding files/patterns |
| **Plan** | Designing implementation strategy for non-trivial features |
| **general-purpose** | Multi-step tasks needing full tool access |

## Hooks (`.claude/hooks/`)

All warn-only (exit 0) except `protect-env-files.sh` which blocks with exit 2.

| Hook | Trigger | Effect |
|------|---------|--------|
| `post-edit-lint.sh` | Edit/Write `*.py` | `ruff check` warnings |
| `post-edit-lint.sh` | Edit/Write `*.ts`/`*.tsx` | `make maintainability-check` warnings |
| `pre-commit-check.sh` | `git commit` via Bash | `make lint && make test` warnings |
| `protect-env-files.sh` | Edit/Write `.env*` | **Blocks** the edit (exit 2) |
| `session-context.sh` | SessionStart (compact) | Re-injects stack/architecture context |
| `notify.sh` | Notification event | Desktop `notify-send` alert (async) |

## Path-scoped rules (`.claude/rules/`)

Loaded automatically when editing files in the matched paths:

| File | Paths | Content |
|------|-------|---------|
| `testing.md` | `backend/tests/**`, `frontend/src/test/**` | pytest/vitest patterns, fixture imports |
| `api-design.md` | `backend/app/api/**`, `services/use_cases/**` | Schema-first edit sequence, route thinness |
| `frontend.md` | `frontend/src/**/*.{ts,tsx}` | shadcn-first, hook boundaries, size limits |

## Context Management

### File read priority

When context is limited, prioritize in this order:
1. Files being changed and their direct imports
2. Related test files
3. Schema definitions (`api/schemas/v1/`)
4. Use-case orchestrators (`services/use_cases/`)
5. Adjacent domain services

### Reducing context pressure

- Use the Explore agent for broad searches instead of reading many files inline
- Read only relevant line ranges of large files (use `offset` + `limit`)
- For frontend changes: read the hook before the component — hooks hold the logic
- For backend changes: read the use-case before the route — routes are thin wrappers
- When touching a domain (wordbank, playground, etc.), read its hook + section + tests as a unit

### Memory guidance

Worth saving to memory (persists across conversations):
- Danish linguistic edge cases and vocabulary decisions
- External API quirks (Azure, Gemini behavior, rate limits, gotchas)
- User preferences for code style or workflow

Not worth saving (derivable from code/docs):
- Architecture patterns — read AGENTS.md and this file instead
- File locations — use Glob/Grep
- Recent git activity — use `git log`
