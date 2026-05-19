# `backend/app/api/schemas/v1/`

Versioned (v1) Pydantic request/response DTOs — the wire contract for the
HTTP API. These are the only models routes should expose; never return
repository-layer dataclasses or domain objects directly.

## File map

| File | Domain |
|---|---|
| `account.py` | Account/me, API-key status, free-trial status + opt-in. |
| `auth.py` | Current-user identity response. |
| `analyze.py` | Note analysis request/response. |
| `developer.py` | Developer-only runtime key/service probes. |
| `guest.py` | Guest session creation request/response. |
| `wordbank.py` | Wordbank CRUD + COR/EN search request/response models. |
| `sentencebank.py` | Sentencebank request/response models. |
| `root.py` | Health/root status payloads. |
| `__init__.py` | Flat re-export barrel; keep `__all__` in sync when adding models. |

## Rules

- One module per API domain; mirror the route module name where practical.
- Add or change a model here **first**, then wire the route/use-case.
- DTO field invariants belong in `docs/contracts/api-contract.md`.
- Repository-layer shapes live in `backend/app/db/repositories/*_models.py`, not here.
