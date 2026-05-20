# `frontend/src/app/sections/sentencebank/`

Sentencebank UI components.

This directory owns the saved-sentence list, sentence detail page, token cards,
generated-example dialog, and small sentencebank-only view helpers.

Use these files for rendering and user events inside the sentencebank section.
Fetching, saving, deletion, pronunciation orchestration, and refresh side
effects belong in hooks under `frontend/src/app/hooks/`.

`sentencebank-list-view.tsx` handles the collection view and row-level actions.
`sentencebank-sentence-page.tsx` handles a single sentence and its token cards.
`sentencebank-token-button.tsx` renders individual saved or unsaved token
buttons.

Keep shared language or formatting utilities in `frontend/src/app/core/`, not
in this directory. If a dialog or panel grows beyond a simple inline flow,
extract it to a sibling component so list/detail files stay readable.
