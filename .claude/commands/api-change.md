---
description: Guide through the mandatory schema-first workflow for any API change. Invoke with a description of the change.
---

You are guiding an API change in the danote project. The user wants to make the following change:

**$ARGUMENTS**

Follow the mandatory edit sequence from AGENTS.md exactly. Do not skip steps.

---

## Step 1 — Read current state

Before touching any code:
1. Read `docs/api-contract.md` — find the affected route(s) and current schema
2. Read the relevant schema file(s) in `backend/app/api/schemas/v1/`
3. Read the relevant route handler(s) in `backend/app/api/routes/`
4. Read the relevant use-case(s) in `backend/app/services/use_cases/`

Summarize what currently exists and what needs to change.

---

## Step 2 — Update schema first

Edit the request/response DTO(s) in `backend/app/api/schemas/v1/` before touching anything else.

Rules:
- Never define models inline in route files — schemas live in `api/schemas/v1/` only
- If adding a new field, make it optional with a default unless there's a strong reason
- If removing a field, check all callers first

---

## Step 3 — Update use-case logic

Edit `backend/app/services/use_cases/` to implement the new behavior.
Keep the route handler thin — no business logic should move into the route.

---

## Step 4 — Update route handler (minimal)

Edit `backend/app/api/routes/` only to:
- Wire the updated schema types
- Delegate to the updated use-case
- Map errors to appropriate HTTP status codes

---

## Step 5 — Write or update tests

Target tests nearest to the changed boundary:
- Use-case logic → `backend/tests/use_cases/`
- HTTP shape/status → `backend/tests/api/`
- Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/`

---

## Step 6 — Update docs/api-contract.md

Update the affected route entry to match the new schema. Format:
```markdown
### METHOD `/api/path`
- **Request model:** `ModelName` (or "none").
- **Response model:** `ModelName`.
- **Notable status/error behavior:** list status codes.
```

---

## Step 7 — Verify

```bash
make lint
make test
bash ./scripts/pytest-backend.sh -q tests/use_cases
```

Confirm all pass before declaring done.
