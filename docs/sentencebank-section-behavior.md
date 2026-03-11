# Sentencebank Section Behavior

This document describes how the Sentencebank section is populated, rendered, and refreshed in the frontend.

## 1) Entry points

### UI section renderer

- The Sentencebank screen is rendered by `SentencebankSection` in `frontend/src/app/sections/sentencebank-section.tsx`.
- It receives three props: `sentencebankError`, `isSentencebankLoading`, and `sentences`.

### Sentence add flow from Playground

- `addSentenceToSentencebank` lives in `frontend/src/app/hooks/use-wordbank-workflows.ts`.
- The flow is:
  1. Normalize selected text by collapsing all whitespace runs to single spaces and trimming ends.
  2. Enforce minimum phrase shape (`hasMultipleWords`) before allowing save.
  3. Build a normalized key (`normalizePhraseKey`) and block duplicates against existing sentencebank entries.
  4. POST to `/api/sentencebank/sentences` with `{ source_text: normalizedSelection }`.
  5. On success, toast success, increment `sentencebankRefreshTick`, and invoke optional `onSentenceSaved` callback.
  6. On failure, toast an error and always clear the local saving flag in `finally`.

## 2) Loading and error states

The section has a strict render priority in `SentencebankSection`:

1. **Error state first**
   - If `sentencebankError` exists, render a `<p role="alert">` with destructive text style.
2. **Initial loading skeleton**
   - If `isSentencebankLoading` is true **and** `sentences.length === 0`, render two skeleton cards.
   - This means the skeleton is only shown when there is no previously loaded sentence data.
3. **Empty state**
   - If not in error/skeleton and `sentences.length === 0`, show:
   - `No saved sentences yet. Select a sentence in Playground to add one.`
4. **List state**
   - Otherwise render sentence cards in a scroll area.

## 3) Add constraints from Playground

`addSentenceToSentencebank` enforces these constraints before writing:

- **Whitespace normalization**
  - `selectedText.replace(/\s+/gu, " ").trim()` is applied first.
- **Multi-word requirement**
  - Empty selections and single-word selections are ignored using `hasMultipleWords`.
- **Duplicate detection by normalized key**
  - The candidate sentence and each existing `sentence.source_text` are compared via `normalizePhraseKey`.
  - If any normalized key matches, no request is sent.

These guards keep sentencebank inserts idempotent from the UI perspective, even when raw spacing/casing differs.

## 4) List rendering semantics

Each list row renders:

- `source_text` as primary line.
- `english_translation` as secondary line with fallback behavior:
  - If translation is null/undefined/blank after trim, render `No translation available.`.

This means whitespace-only translations are intentionally treated as missing.

## 5) Refresh / invalidation behavior

Sentencebank fetching is handled by `useLexiconData`.

- The sentence loader effect depends on `[apiClient, sentencebankRefreshTick]`.
- On every tick change, it:
  - sets `isSentencebankLoading` true,
  - clears `sentencebankError`,
  - fetches `/api/sentencebank/sentences`,
  - stores `payload.items ?? []` on success,
  - stores empty list + error on failure,
  - ends by setting loading false.
- `addSentenceToSentencebank` increments `sentencebankRefreshTick` after successful save.

Result: successful sentence insertions trigger deterministic re-fetch of the sentence list.

## 6) Test map

Current tests that directly/indirectly cover sentencebank behavior:

- `frontend/src/test/app/app-sentencebank.test.tsx`
  - Verifies saved sentence items are shown in Sentencebank section when fetched.
- `frontend/src/test/app/app-shell-search-basics.test.tsx`
  - Verifies Sentencebank navigation entry exists in shell/sidebar.
- `frontend/src/test/app/app-shell-search-actions.test.tsx`
  - Verifies translation fallback string is not shown when translation data is present in a word detail/search path (relevant to shared fallback semantics).

Playground phrase-action coverage notes:

- `frontend/src/test/app/app-playground-actions.test.tsx` validates playground popover action mechanics for adding words (request, re-analysis, toasts).
- There is currently no dedicated test that exercises the full phrase `Add to sentencebank` action path (normalization, duplicate suppression, and tick-driven refetch) end-to-end in one test file.
