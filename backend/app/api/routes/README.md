# `backend/app/api/routes/`

FastAPI route modules. These files are transport adapters only: parse request
DTOs, call a use-case, map expected errors through route helpers, and return
API DTOs or binary responses.

## What Lives Here

- `root.py`, `health`-style routes, and small feature entry points.
- `wordbank.py` for wordbank lexeme/search/verification endpoints.
- `wordbank_audio.py` for wordbank, number, and presaved-word pronunciation
  endpoints.
- `sentencebank.py` for sentence save/list/preview/pronunciation endpoints.

## What Does Not Live Here

- Business orchestration belongs in `backend/app/services/use_cases/`.
- Direct DB, NLP, or provider access belongs below the use-case layer.
- Request/response model definitions belong in `backend/app/api/schemas/v1/`.

## Choosing A File

- Add new wordbank JSON endpoints to `wordbank.py` unless they are specifically
  pronunciation/audio related.
- Add binary or seeding pronunciation endpoints to `wordbank_audio.py`.
- Keep route functions thin; if the lambda grows, add a use-case method instead.
