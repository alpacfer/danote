# 0001: Use-case orchestration layer in backend

- Status: Accepted
- Date: 2026-02-25

## Context

Route handlers had accumulated orchestration logic, making transport concerns and business flow tightly coupled.

## Decision

Adopt `backend/app/services/use_cases/` as the application orchestration boundary.
Routes remain responsible for request validation, dependency retrieval, and HTTP error mapping.

## Consequences

- Better unit-testability of orchestration logic.
- Thinner route handlers and clearer layering.
- Additional file/module surface to maintain.

## Alternatives considered

- Keep orchestration in routes (rejected: poor separation).
- Introduce framework-level DI container (deferred as unnecessary complexity).
