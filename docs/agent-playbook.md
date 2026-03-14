# Agent Playbook

A compact operational playbook for AI agents modifying this repository.

## 1) Understand the boundaries

- **Transport boundary**: API routes in `backend/app/api/routes/`.
- **Contract boundary**: request/response schemas in `backend/app/api/schemas/v1/`.
- **Orchestration boundary**: use-cases in `backend/app/services/use_cases/`.
- **Domain boundary**: classifier/typo/NLP and related services in `backend/app/services/` and `backend/app/nlp/`.

## 2) Preferred edit strategy

1. Update contract model(s) in `api/schemas/v1/` (if API shape changes).
2. Update use-case behavior in `services/use_cases/`.
3. Keep route updates minimal (validation + HTTP error mapping + invocation).
4. Add tests nearest to the changed boundary.

## 2a) Frontend UI workflow

For any frontend/UI change:

1. Read the relevant repo docs and inspect the local component patterns first.
2. Review the official shadcn/ui docs for the likely candidate components.
3. Choose the best-fit primitive and note why adjacent options were rejected when that choice affects structure or interaction.
4. If the chosen component is missing locally, install it with `npx shadcn@latest add <component>`.
5. Compose the feature from shadcn primitives before introducing custom UI building blocks.
6. Update tests and documentation in the same change.

## 3) Verification strategy

Run this exact sequence for deterministic confidence:

```bash
make lint
make maintainability-check
make test
make docs-smoke
```

Backend pytest restores the tracked Gemini audit log
`backend/data/gemini-applied-changes.jsonl` when the session finishes, so
verification/apply-change tests do not require manual cleanup.

If backend orchestration changed, also run:

```bash
bash ./scripts/pytest-backend.sh -q tests/use_cases
```

## 4) Maintainability budgets and exemptions

- Budget thresholds and exemptions are defined in `docs/maintainability-budgets.md`.
- Exemptions are allowlist-only and limited to intentional generated/vendor files.
- Any allowlist change must include rationale in the same PR.

## 5) Common pitfalls

- Editing route files to include business logic (should be in use-cases).
- Duplicating schemas in route files (use `api/schemas/v1/`).
- Updating docs commands without updating smoke scripts.

## 6) Definition of done for agent-generated PRs

- Code compiles/lints in the maintained checks.
- Existing tests pass; new behavior has tests.
- Docs and scripts are aligned with run instructions.
- PR summary references commands actually executed.
