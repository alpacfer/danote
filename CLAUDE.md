# CLAUDE.md

AI agent context for danote: Danish-first language-learning app. `frontend/` React+Vite, `backend/` FastAPI+SQLite+NLP.

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

File map:
- Routes: `backend/app/api/routes/`
- DTOs: `backend/app/api/schemas/v1/`
- Use-cases: `backend/app/services/use_cases/`
- Domain services: `backend/app/services/`
- NLP: `backend/app/nlp/`
- DB: `backend/app/db/`

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

### Quick file lookup

- Backend entry: `backend/app/main.py`
- API router: `backend/app/api/router.py`
- Frontend entry: `frontend/src/App.tsx`
- E2E: `scripts/e2e-regression.sh`
- Docs smoke: `scripts/docs-smoke.sh`

## Agents

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

Warn-only (exit 0) except `protect-env-files.sh` (exit 2 blocks).

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

Reduce pressure: Explore agent for broad searches; read hook before component; read use-case before route; read hook + section + tests as unit per domain.

## Verification

Run smallest set covering changed boundary. Escalate for broad/risky changes:
1. `make lint`
2. `make test`
3. `make docs-smoke`

Backend orchestration/schema changes: `bash ./scripts/pytest-backend.sh -q tests/use_cases`
Targeted: frontend-only → nearest Vitest; backend-only → nearest pytest; docs-only → `make docs-smoke`

## Change Policy

- Routes thin; orchestration in `services/use_cases/`.
- DTOs in `api/schemas/v1/` first; routes import from schemas.
- Prefer adding/expanding tests over silently changing expectations.
- Smallest verification set proving changed behavior.
- Update docs when command/workflow behavior changes.
- Frontend: existing shadcn/ui before custom UI. Review shadcn docs first.
- Install shadcn: `npx shadcn@latest add <component>` with defaults. Don't handcraft.
- Frontend workflow: review docs → review shadcn docs → install primitive → compose → test → doc.

## Documentation Sync (mandatory)

- Read related docs (`README.md`, `docs/`) before implementing.
- Any code/config/API/schema change → update docs same PR.
- No doc changes → PR must include "No documentation impact" justification.
- API route/schema changes → `docs/contracts/api-contract.md`.
- Command/setup changes → `README.md` + `docs/`.
- Version/dep changes → `docs/reference/versions.md`.
- Completion checklists → explicit docs parity checkbox.

## Maintainability

- UI components: render + handle UI events only. Data fetching/side effects in hooks/services.
- Don't add feature logic to large files without extracting first.

### File size limits

- `*.ts`/`*.tsx`: target ≤300, soft ≤450, hard >450 → refactor.
- React components: target ≤200 lines, one concern.
- Custom hooks: target ≤220 lines, one workflow.
- Functions: target ≤60 lines.
- Test files: target ≤1200 lines.

### Refactor triggers

- Touch file >450 lines + add non-trivial logic → split same change.
- Component handles 3+ domain workflows → extract hooks.
- Prop list ≥15 → group into typed objects or split.
- Generic file (`utils.ts`) grows → split by domain.

### Organization

- Domain folders over flat (`hooks/playground/*`, `hooks/wordbank/*`).
- `App.tsx` composes, no workflow logic.
- Backend layering strict: routes → schemas → use-cases → domain services.
- Module APIs explicit; export stable hooks/components from index barrels.

### Type safety

- Avoid `any`; explicit types at boundaries.
- State shapes typed + named by domain.
- Small intention-revealing names.
- Comments only where non-obvious.

## Verification Before Finishing

- Targeted checks covering changed files/behavior by default.
- Full suite for broad/high-risk changes (refactors, workflow/build/dep changes, unclear blast radius).
- If behavior moved → tests still cover moved behavior.
- Final summary: call out extracted modules.

## Self-Verification Checklist

- [ ] Docs reviewed before impl (`README.md` and/or `docs/*`)
- [ ] Verification for changed boundary executed + passes
- [ ] Broad changes: `make lint`, `make test`, `make docs-smoke` pass
- [ ] Backend orchestration changed: `tests/use_cases` passes
- [ ] Docs parity verified (updated or "No documentation impact")
- [ ] No unstaged/untracked scratch files
