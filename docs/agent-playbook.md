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

## 3) Verification strategy

Run this exact sequence for deterministic confidence:

```bash
make lint
make test
make docs-smoke
```

If backend orchestration changed, also run:

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_use_cases_unit.py
```

## 4) Common pitfalls

- Editing route files to include business logic (should be in use-cases).
- Duplicating schemas in route files (use `api/schemas/v1/`).
- Updating docs commands without updating smoke scripts.

## 5) Definition of done for agent-generated PRs

- Code compiles/lints in the maintained checks.
- Existing tests pass; new behavior has tests.
- Docs and scripts are aligned with run instructions.
- PR summary references commands actually executed.
