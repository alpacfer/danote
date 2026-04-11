# 0001: Use-case orchestration layer in backend

- Status: Accepted
- Date: 2026-02-25

## Context

Route handlers accumulated orchestration logic; transport concerns and business flow tightly coupled.

## Decision

Adopt `backend/app/services/use_cases/` as application orchestration boundary.
Routes: request validation, dependency retrieval, HTTP error mapping.

## Consequences

- Better unit-testability of orchestration logic.
- Thinner route handlers, clearer layering.
- More file/module surface to maintain.

## Alternatives considered

- Keep orchestration in routes (rejected: poor separation).
- Introduce framework-level DI container (deferred: unnecessary complexity).