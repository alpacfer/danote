# Sentencebank Section Behavior

## 1) Entry points

### UI section renderer

`SentencebankSection` in `frontend/src/app/sections/sentencebank-section.tsx`. Props: `sentencebankError`, `isSentencebankLoading`, `sentences`.

### Sentence add flow from Playground

`addSentenceToSentencebank` in `frontend/src/app/hooks/use-wordbank-workflows.ts`:
1. Normalize selected text: collapse whitespace to single spaces, trim
2. Enforce `hasMultipleWords` before allowing save
3. Build `normalizePhraseKey`, block duplicates against existing entries
4. `POST /api/sentencebank/sentences` with `{ source_text: normalizedSelection }`
5. Success → toast, increment `sentencebankRefreshTick`, invoke `onSentenceSaved`
6. Failure → toast error, clear saving flag in `finally`

## 2) Loading and error states

Render priority in `SentencebankSection`:
1. **Error** — `sentencebankError` exists → `<p role="alert">` with destructive text
2. **Skeleton** — `isSentencebankLoading && sentences.length === 0` → two skeleton cards (only when no prior data)
3. **Empty** — `sentences.length === 0` → `No saved sentences yet. Select a sentence in Playground to add one.`
4. **List** — sentence cards in scroll area

## 3) Add constraints from Playground

`addSentenceToSentencebank` guards:
- **Whitespace normalization**: `selectedText.replace(/\s+/gu, " ").trim()`
- **Multi-word requirement**: empty/single-word selections ignored (`hasMultipleWords`)
- **Duplicate detection**: compare via `normalizePhraseKey` against existing `sentence.source_text`; match → no request

Inserts are idempotent from UI perspective regardless of spacing/casing differences.

## 4) List rendering

Each row: `source_text` primary line, `english_translation` secondary line. Translation fallback: null/undefined/blank-after-trim → `No translation available.` Whitespace-only translations treated as missing.

## 5) Refresh / invalidation

`useLexiconData` handles fetching. Sentence loader effect depends on `[apiClient, sentencebankRefreshTick]`. Tick change → set loading true, clear error, fetch `/api/sentencebank/sentences`, store `payload.items ?? []` on success / empty list + error on failure, set loading false. `addSentenceToSentencebank` increments tick after successful save → triggers re-fetch.

## 6) Test map

- `frontend/src/test/app/app-sentencebank.test.tsx` — saved sentence items shown when fetched
- `frontend/src/test/app/app-shell-search-basics.test.tsx` — Sentencebank nav entry in shell/sidebar
- `frontend/src/test/app/app-shell-search-actions.test.tsx` — translation fallback string absent when data present

Note: `frontend/src/test/app/app-playground-actions.test.tsx` covers popover action mechanics for adding words. No dedicated end-to-end test exercises full `Add to sentencebank` path (normalization, duplicate suppression, tick refetch) in one file.
