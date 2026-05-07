# `wordbank/collaborators/`

Wordbank-flow-specific helpers. Each file extends the behavior of one or more wordbank use-cases (in the parent `wordbank/` directory) by wrapping or composing the generic services in `backend/app/services/`.

## Why this exists

The generic `backend/app/services/` modules (`cor.py`, `translation.py`, `verification.py`, etc.) are reusable across all use-cases — sentencebank, analyze, developer, etc. When wordbank needs a richer or specialized form (e.g. wordbank-only translation fallback chains, wordbank verification history flow), it lives here.

## Naming pairs

For these names, the file in this directory is wordbank-specific and the file in `backend/app/services/` is generic:

- `cor.py`, `cor_actions.py`, `cor_local.py`, `cor_local_translations.py`, `cor_resolution.py`
- `translation*.py` (12+ variants — fallbacks, helpers, language detection, meaning selection, sentence ops, etc.)
- `verification*.py` (apply flow, change log, history, missing translation, review flow)

## Edit here vs. in `services/`

- **Edit here** when the change only matters inside a wordbank use-case.
- **Edit `backend/app/services/`** when the change should benefit other use-cases too (sentencebank, analyze).

## Size budget

Several files here are over the 450-line hard cap. When touching them, prefer extracting a sibling file (e.g. `verification_apply_flow.py` is already split off `verification.py`) over adding more logic to the existing file.
