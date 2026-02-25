# 0002: Versioned API schemas (`v1`) as DTO boundary

- Status: Accepted
- Date: 2026-02-25

## Context

Request/response models were previously defined inside route modules, increasing drift risk.

## Decision

Centralize API DTOs in `backend/app/api/schemas/v1/` and import them from routes.

## Consequences

- Explicit API contract boundary.
- Easier version migration path (`v2`, etc.).
- Slightly more indirection when reading route files.

## Alternatives considered

- Keep DTOs local to route files (rejected: duplication/drift risk).
- Generate DTOs from OpenAPI first (deferred: premature for current scale).
