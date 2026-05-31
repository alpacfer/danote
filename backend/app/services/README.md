# `backend/app/services/`

Domain services and external adapters. Flat layout (no subdirs). Each file is a single concern — translation provider, COR adapter, verification primitive, etc.

## What goes here

- **External adapters**: `gemini_translation*.py`, `deepl_translation.py`, `tts.py` — talk to third-party APIs. Successful deterministic Gemini contextual translations are persisted by `gemini_contextual_translation_cache.py`.
- **Local lexicon adapters**: `cor.py`, `cor_local*.py`, `en_local*.py` — read bundled dictionary assets.
- **Domain primitives**: `verification*.py`, `token_classifier.py`, `text_preprocessing.py`, `fuzzy_search.py`, `related_words.py`, `sentence_verification.py`.
- **Generic translation adapters**: `translation.py`, `deepl_translation.py`, and
  their bounded successful-result cache in `translation_result_cache.py`.

## What does NOT go here

- **Use-case orchestration** (combining multiple services to satisfy a route) → `services/use_cases/`.
- **Wordbank-specific compositions** (a wordbank flow that wraps a service) → `services/use_cases/wordbank/collaborators/`.
- **Database access** → `db/repositories/`.
- **HTTP request/response models** → `api/schemas/v1/`.

## Naming conflicts to know

The same names appear in `services/use_cases/wordbank/collaborators/`:

| File here (generic, reusable) | File in `collaborators/` (wordbank-flow specific) |
|---|---|
| `services/cor.py` | `collaborators/cor.py` |
| `services/translation.py` | `collaborators/translation.py` |
| `services/verification.py` | `collaborators/verification.py` |

Rule of thumb: edit `services/` if the change is reusable across use-cases. Edit `collaborators/` if it only matters in a wordbank flow.
