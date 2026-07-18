# `frontend/src/app/sections/wordbank/`

Wordbank section views and small render helpers.

## What Lives Here

- `wordbank-word-page.tsx` composes the selected lemma page.
- `wordbank-lemma-header.tsx`, `wordbank-meaning-sections.tsx`, and related files render word detail regions.
- `wordbank-list-results.tsx`, `wordbank-specimen-tile.tsx`, `wordbank-specimen-preview.tsx`, `wordbank-specimen-preview-data.ts`, and `wordbank-reference-decks.tsx` render the saved collection list and its metadata preview.
- `wordbank-alphabet-index.tsx` renders Danish A–Å navigation; `wordbank-alphabet.ts` tracks the visible group.
- `wordbank-paradigm-utils.ts` builds noun/adjective/verb table data from saved surface forms.
- `wordbank-pronunciation-word.tsx` is the shared clickable pronunciation trigger.
- Pinned reference pages live in domain subfolders such as `numbers/`, `pronouns/`, and `time-expressions/`.

## What Does Not Live Here

- Fetching, saves, and side effects belong in hooks under `frontend/src/app/hooks/`.
- API types and morphology helpers belong in `frontend/src/app/core/`.
- shadcn primitives stay in `frontend/src/components/ui/`.

## Choosing A File

- Put render-only word-page changes next to the visible region they affect.
- Put shared table classification in `wordbank-paradigm-utils.ts`.
- Put reusable wordbank-only visual helpers here or in `_shared/`.
- Avoid adding workflow state to these components; pass callbacks from hooks.
