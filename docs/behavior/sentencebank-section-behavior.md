# Sentencebank Section Behavior

## 1) Entry points

### UI section renderer

`SentencebankSection` in `frontend/src/app/sections/sentencebank-section.tsx`. Props: `sentencebankError`, `isSentencebankLoading`, `sentences`, `onOpenWordbankLemma`, `onOpenWordbankMeaning`.

### Sentence add flow from Playground

`addSentenceToSentencebank` in `frontend/src/app/hooks/use-wordbank-workflows.ts`:
1. Normalize selected text: collapse whitespace to single spaces, trim
2. Enforce `hasMultipleWords` before allowing save
3. Build `normalizePhraseKey`, block duplicates against existing entries
4. `POST /api/sentencebank/sentences` with `{ source_text: normalizedSelection }`
5. Success → toast, increment `sentencebankRefreshTick` and `wordbankRefreshTick`, invoke `onSentenceSaved`
6. Failure → toast error, clear saving flag in `finally`
7. Backend also queues sentence-level pronunciation generation when TTS is configured; the hydrated sentence payload returns `has_pronunciation=false` initially plus `pronunciation.status = "queued"`

### Sentence add flow from Sidebar Search

`useSidebarSearch` + `AppSidebar` sentence mode:
1. Normalize query for sentence mode after raw input is preserved in the command field
2. After an adaptive debounce, request `POST /api/sentencebank/search-preview` twice in parallel for the same query: first with `fast=true`, then with `fast=false`
3. Fast preview can render immediately while the full verified result is still pending; the full result overwrites the fast result when it arrives
4. Backend returns the finalized Danish sentence candidate to save, its English translation, detected query language, and any verification findings
5. English-origin previews show an inline translation-origin indicator before save
6. Search save uses `preview.source_text` only, so English-origin queries save the backend-finalized Danish sentence rather than the original English input
7. Save still calls the same `addSentenceToSentencebank` workflow and therefore keeps existing refresh and pending-page behavior

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

Each row renders:
- `source_text` primary line
- `english_translation` secondary line, rendered with sentence-style capitalization (`No translation available.` fallback)
- token-card grid in sentence order when `tokens.length > 0`

Sentence detail page header:
- wraps the rendered sentence line in the shared pronunciation trigger used on word pages
- click plays `/api/sentencebank/pronunciation?sentence_id=<id>`
- right-click opens a context menu with `Say slowly` and `Regenerate audio`
- `Say slowly` reuses the same saved sentence audio but plays it back at a reduced browser playback rate for a slower pronunciation pass
- `Regenerate audio` posts `/api/sentencebank/sentences/pronunciation` with `{ sentence_id, force: true }`
- icon dimming reflects `has_pronunciation`; playback still attempts the fetch so newly generated audio works after refresh

Each token card renders:
- surface form
- linked lemma hint when the saved lemma differs from the surface
- translation/gloss line
- POS/morphology badges
- hover/focus state underlines the matching token inside the sentence line on the sentence page
- click action opening the linked word page (`meaning_id` when present, lemma page otherwise)

## 5) Refresh / invalidation

`useLexiconData` handles fetching. Sentence loader effect depends on `[apiClient, sentencebankRefreshTick]`. Tick change → set loading true, clear error, fetch `/api/sentencebank/sentences`, store `payload.items ?? []` on success / empty list + error on failure, set loading false. `addSentenceToSentencebank` increments tick after successful save → triggers re-fetch.

## 6) Test map

- `frontend/src/test/app/app-sentencebank.test.tsx` — saved sentence items shown when fetched
- `frontend/src/test/app/app-sentencebank.test.tsx` — token cards render and open linked word pages
- `frontend/src/test/app/app-shell-search-basics.test.tsx` — Sentencebank nav entry in shell/sidebar
- `frontend/src/test/app/app-shell-search-actions.test.tsx` — sentence-mode save refreshes sentencebank + wordbank

Note: `frontend/src/test/app/app-playground-actions.test.tsx` covers popover action mechanics for adding words. No dedicated end-to-end test exercises full `Add to sentencebank` path (normalization, duplicate suppression, tick refetch) in one file.
