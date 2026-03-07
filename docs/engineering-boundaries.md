# Engineering Boundaries

danote keeps orchestration and runtime wiring separate on purpose. New code should follow these boundaries:

- Routes are transport adapters only. They validate input, invoke a use case, and translate failures to HTTP.
- `app/bootstrap/` owns app creation, startup wiring, shutdown, and request-level observability.
- `app/core/` owns typed runtime state, configuration, and shared application primitives.
- `app/db/` owns SQLite connection policy, repositories, and migration primitives.
- `app/services/use_cases/` owns workflows and application behavior.
- Provider-specific integrations stay in focused services/collaborators and should not leak network or DB details into routes.

Refactor triggers:

- If a route starts containing branching business rules, move them into a use case or collaborator.
- If a use case opens raw SQLite connections in multiple places, extract or extend a repository first.
- If startup or health logic grows by provider, add or update a bootstrap helper instead of expanding `main.py`.
- If a frontend hook starts mixing transport, error parsing, and UI state, move transport into `app/core/api-client.ts`.

File-size defaults:

- Backend route/bootstrap/core files should target <= 250 lines.
- Backend workflow/repository files should target <= 350 lines unless they are intentionally acting as a public facade.
- Frontend hooks should keep transport calls behind the API client and stay focused on one workflow.
