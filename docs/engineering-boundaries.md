# Engineering Boundaries

danote keeps orchestration/runtime wiring separate. New code follow boundaries:

- Routes: transport adapters only. Validate input, invoke use case, translate failures to HTTP.
- `app/bootstrap/` owns app creation, startup wiring, shutdown, request-level observability.
- `app/core/` owns typed runtime state, config, shared app primitives.
- Access backend runtime state via `app.core.app_state` helpers; don't read/write legacy `app.state.*` fields directly.
- `app/db/` owns SQLite connection policy, repositories, migration primitives.
- `app/services/use_cases/` owns workflows + app behavior.
- Provider integrations stay in focused services/collaborators; don't leak network/DB into routes.

Refactor triggers:

- Route has branching business rules → move to use case/collaborator.
- Use case opens raw SQLite in multiple places → extract/extend repository.
- Startup/health logic grows by provider → add/update bootstrap helper, don't expand `main.py`.
- Frontend hook mixes transport, error parsing, UI state → move transport into `app/core/api-client.ts`.
- UI prop mapping only for one section → keep adapter near that section, don't add generic app-controller plumbing.

File-size defaults:

- Backend route/bootstrap/core files: <= 250 lines.
- Backend workflow/repository files: <= 350 lines unless public facade.
- Frontend hooks: keep transport behind API client, focused on one workflow.

## Wordbank refactor module map (2026-03)

Keep long-running backend files maintainable, preserve stable interfaces:

- `app/db/repositories/wordbank.py` public facade (`WordbankRepository`).
- `app/db/repositories/wordbank_reads.py` owns read/query behavior.
- `app/db/repositories/wordbank_mutations.py` owns mutation/upsert behavior.
- `app/db/repositories/wordbank_models.py` owns shared repository row models + parsers.
- `app/services/gemini_translation.py` keeps service entrypoints/signatures; helper logic delegated to `app/services/gemini_translation_helpers.py`.
- `app/services/use_cases/wordbank/collaborators/translation.py` collaborator facade; language detection/context building/provider fallback delegated to focused collaborators in same folder.

New wordbank behavior: extend focused modules, don't re-grow single impl file.