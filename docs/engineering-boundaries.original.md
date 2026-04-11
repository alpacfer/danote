# Engineering Boundaries

danote keeps orchestration and runtime wiring separate on purpose. New code should follow these boundaries:

- Routes are transport adapters only. They validate input, invoke a use case, and translate failures to HTTP.
- `app/bootstrap/` owns app creation, startup wiring, shutdown, and request-level observability.
- `app/core/` owns typed runtime state, configuration, and shared application primitives.
- Access backend runtime state through `app.core.app_state` helpers; do not read or write legacy `app.state.*` service fields directly.
- `app/db/` owns SQLite connection policy, repositories, and migration primitives.
- `app/services/use_cases/` owns workflows and application behavior.
- Provider-specific integrations stay in focused services/collaborators and should not leak network or DB details into routes.

Refactor triggers:

- If a route starts containing branching business rules, move them into a use case or collaborator.
- If a use case opens raw SQLite connections in multiple places, extract or extend a repository first.
- If startup or health logic grows by provider, add or update a bootstrap helper instead of expanding `main.py`.
- If a frontend hook starts mixing transport, error parsing, and UI state, move transport into `app/core/api-client.ts`.
- If UI prop mapping is only for one section, keep the adapter close to that section instead of adding generic app-controller plumbing.

File-size defaults:

- Backend route/bootstrap/core files should target <= 250 lines.
- Backend workflow/repository files should target <= 350 lines unless they are intentionally acting as a public facade.
- Frontend hooks should keep transport calls behind the API client and stay focused on one workflow.

## Wordbank refactor module map (2026-03)

To keep long-running backend files maintainable while preserving stable interfaces:

- `app/db/repositories/wordbank.py` remains the public facade (`WordbankRepository`).
- `app/db/repositories/wordbank_reads.py` owns read/query behavior.
- `app/db/repositories/wordbank_mutations.py` owns mutation/upsert behavior.
- `app/db/repositories/wordbank_models.py` owns shared repository row models and row parsers.
- `app/services/gemini_translation.py` keeps service entrypoints/signatures; helper logic is delegated to `app/services/gemini_translation_helpers.py`.
- `app/services/use_cases/wordbank/collaborators/translation.py` remains the collaborator facade; language detection/context building/provider fallback are delegated to focused collaborators in the same folder.

When adding new wordbank behavior, prefer extending these focused modules instead of re-growing a single implementation file.
