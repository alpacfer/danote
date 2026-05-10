# `backend/app/services/use_cases/`

Use-case orchestrators. One file (or one subdir for large domains) per route or workflow. Each orchestrator composes services (`backend/app/services/`) and repositories (`backend/app/db/repositories/`) to fulfill a single API call.

## Layout

- `analyze.py`, `developer.py`, `health_status.py`, `numbers_pronunciation.py`, `presaved_words_pronunciation.py`, `static_hv_words.py`, `static_presaved_words.py`, `static_pronouns.py` — small, single-file use-cases.
- `sentencebank*.py` — sentencebank flows (preview, examples, token resolution, pronunciation, persistence).
- `wordbank/` — wordbank flows; large enough to warrant its own subdir with `collaborators/` for shared helpers.

## Rules

- Route handlers in `api/routes/` should call into here, not into services or repositories directly.
- Keep handlers thin — orchestration belongs here.
- A use-case may call multiple services and one or more repositories.
- If two use-cases share a helper, put it in `services/` (if reusable) or in the relevant `collaborators/` directory (if scoped to one domain).

## Verification

`bash ./scripts/pytest-backend.sh -q tests/use_cases` runs the use-case test suite. Run it after any change here.
