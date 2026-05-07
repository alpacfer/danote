# AGENTS.md

Tool-agnostic AI agent context for danote. This is the canonical source of truth — **edit `AGENTS.md`**. `CLAUDE.md` and `AGENT.md` are compatibility symlinks. Claude Code, Codex, and other coding agents all read from here.

## Mission

danote is a Danish-first language-learning notes app.

- `frontend/`: React 19, Vite, TypeScript, Tailwind CSS v4, shadcn/ui
- `backend/`: FastAPI, SQLite, local dictionary assets, translation and verification services

## Commands

Run from the repo root unless noted.

```bash
make setup
make lint
make maintainability-check
make test
make docs-smoke
make agent-verify
make dev
```

Targeted checks:

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/path/to/test_file.py
cd frontend && npx vitest run src/test/path/to/file.test.ts
bash ./scripts/pytest-backend.sh -q tests/use_cases
```

## Architecture

Backend flow: routes -> schemas -> use-cases -> domain services -> adapters -> DB.

- Routes: `backend/app/api/routes/`
- DTOs: `backend/app/api/schemas/v1/`
- Use-cases: `backend/app/services/use_cases/`
- Domain services: `backend/app/services/`
- NLP/adapters: `backend/app/nlp/`
- DB: `backend/app/db/`

Frontend:

- App entry: `frontend/src/App.tsx`
- Sections: `frontend/src/app/sections/`
- Hooks: `frontend/src/app/hooks/`
- Chrome: `frontend/src/app/chrome/`
- UI primitives: `frontend/src/components/ui/`
- Alias: `@/*` -> `./src/*`

Quick lookup:

- Backend entry: `backend/app/main.py`
- API router: `backend/app/api/router.py`
- E2E script: `scripts/e2e-regression.sh`
- Docs smoke: `scripts/docs-smoke.sh`

## Change Policy

- Keep route handlers thin; orchestration belongs in `services/use_cases/`.
- Add or modify API request/response models in `api/schemas/v1/` first.
- Prefer adding or expanding tests over silently changing expectations.
- Use the smallest verification set that proves the changed behavior.
- Escalate to `make lint`, `make test`, and `make docs-smoke` for broad, risky, build, workflow, dependency, or cross-cutting changes.
- For backend orchestration or API schema changes, run `bash ./scripts/pytest-backend.sh -q tests/use_cases`.
- Before code, config, API, schema, or workflow changes, read the related docs in `README.md` and/or `docs/`.
- Update docs in the same change when behavior, command, setup, API, schema, dependency, or runtime expectations change.
- If no docs changed, include a clear "No documentation impact" note in the final PR summary.

Docs map:

- API route/schema changes: `docs/contracts/api-contract.md`
- Command/setup/workflow changes: root `README.md` and relevant `docs/`
- Dependency/runtime changes: `docs/reference/versions.md`
- Behavior changes: matching `docs/behavior/*` doc and `docs/README.md` freshness entry

## Maintainability

- UI components render and handle UI events only.
- Fetching, orchestration, and side effects live in hooks/services.
- Shared pure logic lives in focused utility modules.
- Avoid adding feature logic to already-large files without extracting first.
- Prefer domain folders over flat catch-all directories.
- Keep module APIs explicit; use stable index barrels when useful.
- Avoid `any`; use explicit types at boundaries.
- Use small, intention-revealing names.
- Comments should explain non-obvious intent only.

Size targets:

- Production `*.ts`/`*.tsx`: target <=300 lines, hard >450 requires split/refactor.
- React components: target <=200 lines and one main concern.
- Custom hooks: target <=220 lines and one workflow/domain concern.
- Functions: target <=60 lines.
- Test files: target <=1200 lines.

Refactor triggers:

- Touch a file >450 lines and add non-trivial logic.
- A component handles 3+ domain workflows.
- Prop list reaches roughly 15+ items.
- Generic `utils.ts` or `helpers.ts` grows beyond one clear domain.

## Frontend Rules

- Review existing repo docs and local patterns before UI work.
- Use existing shadcn/ui primitives before custom primitives.
- If a needed shadcn component is missing, install it with `npx shadcn@latest add <component>` using defaults.
- Compose around generated shadcn APIs; do not rewrite generated internals unless explicitly requested.
- Test user-observable behavior, not implementation details.

## Test Rules

Backend tests live under `backend/tests/`:

- Use-case logic: `tests/use_cases/`
- Domain services: `tests/services/`
- HTTP shape/status: `tests/api/`
- DB behavior: `tests/db/`

Backend testing patterns:

- Read nearby tests first and match local style.
- Use dependency injection and fakes from `tests/helpers/`.
- Prefer `_db_path(tmp_path)` for isolated DB paths.
- Put `from __future__ import annotations` at the top of new test files.
- Do not test business logic through route handlers.

Frontend tests live under `frontend/src/test/`:

- Use shared helpers such as `renderApp()` and `mockFetchImplementation()`.
- Interact through Testing Library queries and user-visible outcomes.
- Keep test helpers in `src/test/`.

## Danish Language Notes

- Danish nouns have common/neuter gender and definite suffixes (`-en`, `-et`, `-ne`).
- Verbs commonly inflect as infinitive `-e`, present `-er`, past `-ede`/`-te`/`-de`, participle `-et`/`-t`.
- Danish compounds are single tokens and may not appear in COR in full form.
- `er` lemmatizes to `være`; do not treat it as a regular `-er` verb.
- Word verification may use COR glosses internally, but Gemini review output should stay focused on lemma/meaning translation feedback.
- The previous DaCy/spaCy/Lemmy stack is retired; `DANOTE_NLP_ENABLED` defaults to `0`.

## Subagents

Project-specific Claude Code subagents live in `.claude/agents/` (`danish-linguist`, `test-writer`, `docs-updater`). Codex users can read those files as role briefings. Generic Explore/Plan agents are built into both tools and are not duplicated here.

## Local Safeguards

Keep secrets and generated artifacts out of normal edits:

- Do not read or edit `.env`, `.env.*`, `.env.local`, or `backend/.env*`.
- Do not edit tracked Gemini audit logs unless the task explicitly requires it.
- Do not push without explicit user confirmation.
- Warn before committing if lint/tests have not run.
- Python edits should pass ruff/compile checks for touched backend boundaries.
- TypeScript edits should respect maintainability budgets and nearby Vitest coverage.

Claude-specific runtime hooks and permissions may exist under `.claude/`; they should implement these rules, not redefine project behavior.

## Finish Checklist

- [ ] Related docs reviewed before implementation.
- [ ] Relevant targeted verification ran and passed.
- [ ] Broad/high-risk changes ran `make lint`, `make test`, and `make docs-smoke`.
- [ ] Backend orchestration changes ran `tests/use_cases`.
- [ ] Docs parity verified.
- [ ] No scratch files, caches, duplicate artifacts, or accidental generated files remain.
