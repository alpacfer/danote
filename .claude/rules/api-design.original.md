---
paths:
  - "backend/app/api/**"
  - "backend/app/services/use_cases/**"
---

# API design rules

## Edit sequence (mandatory)

1. Schema DTO in `api/schemas/v1/` first
2. Use-case logic in `services/use_cases/`
3. Route handler last (thin wiring only)

Never define models inline in route files. Routes import from `api/schemas/v1/`.

## Route handlers must stay thin

A route handler should only:
- Validate input (via Pydantic schema)
- Call one use-case method
- Map exceptions to HTTP status codes
- Return a typed response

No business logic, no DB calls, no service calls directly from a route.

## Standard error mapping

| Exception type | HTTP status |
|---|---|
| `ValueError` | 400 |
| DB unavailable / locked | 503 |
| NLP not ready (`require_nlp_ready`) | 503 |
| Not found | 404 |

## API contract sync

Any added, removed, or modified route must update `docs/api-contract.md` in the same change.
Format per endpoint:
```markdown
### METHOD `/api/path`
- **Request model:** `ModelName` (or "none").
- **Response model:** `ModelName`.
- **Notable status/error behavior:** list status codes.
```
