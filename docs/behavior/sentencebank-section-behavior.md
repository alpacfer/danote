# Sentencebank Section Behavior

## 1) Entry points

### UI section renderer

`SentencebankSection` in `frontend/src/app/sections/sentencebank-section.tsx`. Props: `sentencebankError`, `isSentencebankLoading`, `sentences`, `onOpenWordbankLemma`, `onOpenWordbankMeaning`.

### Retired Playground add flow

The previous selected-text save path from Playground is retired while Playground is inaccessible.

### Sentence add flow from Sidebar Search

`useSidebarSearch` + `AppSidebar` sentence mode:
1. Normalize query for sentence mode after raw input is preserved in the command field
2. After an adaptive debounce, request `POST /api/sentencebank/search-preview` twice in parallel for the same query: first with `fast=true`, then with `fast=false`
3. Fast preview can render immediately while the full verified result is still pending; the full result overwrites the fast result when it arrives
4. Backend returns the finalized Danish sentence candidate to save, its English translation, detected query language, and any verification findings
5. English-origin previews show an inline translation-origin indicator before save
6. Search save uses `preview.source_text` only, so English-origin queries save the backend-finalized Danish sentence rather than the original English input
7. Save still calls the same `addSentenceToSentencebank` workflow and therefore keeps existing refresh and pending-page behavior

### Generated example add flow from Wordbank

Meaning cards expose a right-click `Generate example` action. The action calls
`POST /api/sentencebank/example-preview` with the saved lemma and selected
meaning id. The backend uses Gemini with the saved meaning context and returns a
short Danish example plus English translation.

The generated example opens in a dialog over the current section:
- `Save` persists the sentence with `token_persistence_mode = "link_existing_only"`, the generated English translation, and the originating word target.
- `Regenerate` requests a fresh preview for the same saved meaning and replaces the current preview without saving.
- `Discard`/close clears the preview without saving.
- The dialog shows only the Danish example and English translation; pronunciation controls and token cards are not shown or generated until after save.
- The generated Danish example starts lowercase and does not end with a period.
- The originating word is linked as already saved after save; other tokens stay as `save_status = "unsaved"` cards so the user can add them manually from the persisted sentence page.
- Clicking plus on an unsaved card calls `POST /api/sentencebank/sentences/{sentence_id}/tokens/{token_index}/save`, which resolves only that token through the same backend sentence-token resolver used by normal sentence saves. This preserves the generated-example rule that other words are not auto-saved while still resolving verbs and inflected forms from COR surface data when NLP metadata is thin or unavailable.

## 2) Loading and error states

Render priority in `SentencebankSection`:
1. **Error** — `sentencebankError` exists → `<p role="alert">` with destructive text
2. **Skeleton** — `isSentencebankLoading && sentences.length === 0` → two skeleton cards (only when no prior data)
3. **Empty** — `sentences.length === 0` → `No saved sentences yet.`
4. **List** — sentence cards in scroll area

## 3) Add constraints

Sentence saves guard:
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
- pending saves open the sentence detail page immediately with surface-form word cards derived from the finalized Danish sentence, while still showing loading placeholders for unknown token metadata

Each token card renders:
- surface form
- linked lemma hint when the saved lemma differs from the surface
- translation/gloss line
- POS/morphology badges
- hover/focus state underlines the matching token inside the sentence line on the sentence page
- click action opening the linked word page (`meaning_id` when present, lemma page otherwise)
- unsaved generated-example tokens render with the plus icon and click into the existing add-word flow for that surface

While full NLP is retired, sentence saves still use a lightweight word tokenizer so the sentence page keeps one card per saved word. Existing saved words are linked when possible; otherwise the fallback creates root-level wordbank entries without POS/morphology metadata.

Known Danish pronouns, question words, prepositions, conjunctions, and
calendar terms (days, months, seasons) all use static built-in catalogs
before COR, translation, or Gemini selection. Saved sentence tokens for
these built-ins carry hardcoded translation, POS, and morphology metadata
and open the matching Wordbank pinned reference page (e.g. pronoun tokens
open Personal / Possessive / Demonstrative / Relative / Indefinite Pronouns
based on lemma; interrogatives open Question Words; `i`, `på`, `og`, `at`,
`mandag`, etc. open the corresponding function-word or calendar page).

## 5) Refresh / invalidation

`useLexiconData` handles fetching. Sentence loader effect depends on `[apiClient, sentencebankRefreshTick]`. Tick change → set loading true, clear error, fetch `/api/sentencebank/sentences`, store `payload.items ?? []` on success / empty list + error on failure, set loading false. `addSentenceToSentencebank` increments tick after successful save → triggers re-fetch.

## 6) Test map

- `frontend/src/test/app/app-sentencebank.test.tsx` — saved sentence items shown when fetched
- `frontend/src/test/app/app-sentencebank.test.tsx` — token cards render and open linked word pages
- `frontend/src/test/app/app-sentencebank.test.tsx` — unsaved generated-example token cards trigger add-word
- `frontend/src/test/app/app-wordbank-actions.test.tsx` — meaning-card example preview generate/regenerate/save flow
- `frontend/src/test/app/app-shell-search-basics.test.tsx` — Sentencebank nav entry in shell/sidebar
- `frontend/src/test/app/app-shell-search-actions.test.tsx` — sentence-mode save refreshes sentencebank + wordbank

No active Playground test coverage remains because the section is retired/inaccessible.
