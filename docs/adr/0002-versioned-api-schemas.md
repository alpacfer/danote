# 0002: Versioned API schemas (`v1`) as DTO boundary

- Status: Accepted
- Date: 2026-02-25

## Context

Request/response models defined inside route modules before. Drift risk high.

## Decision

Centralize API DTOs in `backend/app/api/schemas/v1/`. Import from routes.

## Consequences

- Explicit API contract boundary.
- Easier version migration (`v2`, etc.).
- More indirection in route files.

## Alternatives considered

- DTOs local to route files (rejected: duplication/drift risk).
- Generate DTOs from OpenAPI first (deferred: premature for current scale).