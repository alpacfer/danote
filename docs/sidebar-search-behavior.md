# Sidebar search behavior deep dive

This document describes the **current, exact behavior** of the sidebar command search ("Search words and notes...") as implemented in the frontend.

## Entry points and core modules

- UI shell and dialog wiring: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`
- Query + API orchestration: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
- Ranking + de-duplication logic: `frontend/src/app/chrome/sidebar/use-sidebar-search-ranking.ts`
- Rendering of grouped results and actions:
  - `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`
  - `frontend/src/app/chrome/sidebar/sidebar-wordbank-results.tsx`
  - `frontend/src/app/chrome/sidebar/sidebar-cor-results.tsx`

## Open/close and input behavior

- The search dialog opens from:
  - sidebar "Search..." button
  - keyboard hotkey (`Cmd/Ctrl+K`)
- Closing the dialog always clears:
  - `searchQuery`
  - command selection override
- Input updates are normalized via `normalizeSearchWord(...)` before state is stored.
- Placeholder text is: `Search words and notes...`

## Data sources queried by search

The dialog combines results from three sources:

1. **Saved wordbank items** (backend search endpoint)
2. **COR form analyses** (backend COR endpoint, two-phase fetch)
3. **Saved notes** (local in-memory filter)
4. **Static page navigation items** (Playground/Notes/Wordbank/Sentencebank/Developer)

### Notes filtering

- Notes are only considered when `normalizedQuery` is non-empty.
- Matching checks both `note.name` and `note.text` using case-insensitive Danish locale (`da-DK`) includes.
- Notes are limited to the first 8 matches.

### Page filtering

- With an empty query, all page items are shown.
- With a non-empty query, pages are filtered by case-insensitive `da-DK` includes on page label.

## Saved wordbank API behavior

Endpoint:

- `GET /api/wordbank/search?query=<q>&limit=8`

Behavior:

- Calls are debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`.
- Calls are skipped when query length `< 2`.
- Results are cached by normalized query.
- On cache hit, cached results are reused.
- On error or empty payload, wordbank matches become empty.
- Importantly, only **exact-ish** API rows are kept:
  - keep row if normalized `lemma === normalizedQuery`
  - or normalized `match_surface === normalizedQuery`
  - all other API rows are discarded in the sidebar.

## COR form API behavior

Endpoint:

- `GET /api/wordbank/search/cor-form?form=<q>&limit=100&include_translations=false`
- `GET /api/wordbank/search/cor-form?form=<q>&limit=100`

Behavior:

- COR search is skipped when:
  - query is empty
  - query contains whitespace
  - query is considered a short letter word (`isShortLetterWord(...)`)
- Calls are debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`.
- Two-phase fetch strategy:
  1. Fetch partial payload without translations and render quickly.
  2. Fetch full payload with translations and replace payload.
- While phase 2 is in-flight, `isCorTranslationsLoading=true` and result rows show skeleton placeholders for translation-dependent text.
- While phase 2 is in-flight, COR save rows are disabled.
  They keep the loading skeletons visible but do not render extra locked-state copy during loading.
- Full payload is cached by normalized query.
- If translation fetch fails, a toast error is shown and already-fetched partial results remain visible.
- Single-word translation labels are normalized after provider lookup:
  content-word results drop obvious frame scaffolding but may keep short multi-word phrases,
  while function words keep only minimal lexicalized context when needed.

## Cache invalidation behavior

When `wordbankCacheVersion` changes:

- wordbank search cache is cleared
- COR cache is cleared
- displayed API/COR search results are reset asynchronously

This ensures new saves/edits are reflected in subsequent searches.

## Ranking and ordering behavior

### Saved-wordbank rows

Saved rows are sorted by score descending (then lemma locale sort, then meaning id):

1. exact saved variation (`isExactSaved`) -> 520
2. lemma exact match -> 480
3. linked variation form exact match -> 400
4. `match_surface` exact match -> 360
5. linked variation form contains query -> 280
6. `match_surface` contains query -> 240
7. lemma starts with query -> 200
8. otherwise -> 0

### COR groups

COR groups are sorted by best variant score in each group:

- exact variation-add candidate whose meaning matches a saved wordbank entry -> 400
- other variation-add candidate whose meaning matches a saved wordbank entry -> 320
- exact form match -> 240
- form prefix match -> 160
- fallback tie-break: group lemma locale compare (`da-DK`)

## De-duplication and visibility rules

- COR variants whose `cor_id` is already present in saved `query_cor_ids` are hidden.
- COR variants already linked as add-variation targets for a saved result are hidden from standalone COR list.
- Prefix-only saved matches are hidden because sidebar keeps exact lemma/surface API matches only.

## Row presentation details

### Saved word rows

- Primary title uses this precedence:
  1. linked display variant form
  2. exact matched surface form
  3. `display_lemma`
  4. `lemma`
- "from <lemma>" hint appears when a linked lemma context exists.
- Saved-row translation text uses `english_translation` alone, or `english_translation, gloss_translation` when both exist and differ.
- Raw `gloss` is never appended to saved-row translation text.
- Second line is hidden for exact saved-surface links without gloss.
- Badges:
  - from linked variant `gram_raw` when a display variant is used
  - otherwise from saved row `pos_tag`/`morphology`
- Right icon:
  - `Eye` for open existing saved item
  - `variation + Plus` when selecting row will add a new variation
- When a saved row has a linked variation-add candidate but COR translation is still loading or ultimately unavailable,
  the row stops acting as add-variation and falls back to opening the saved wordbank entry instead.
  In that locked state it shows `Eye` plus inline copy:
  - `Translation required before saving.` when the final COR payload still has no lemma translation

### COR rows

- Always show `variant.form` as primary title.
- May show "from <lemma>" with translation in parentheses when available.
- Sense-level gloss translation is rendered as separate disambiguation text, not as a fallback English translation.
- During translation loading, translation-dependent text uses skeleton placeholders.
- COR add rows are disabled until lemma translation is available.
  They show:
  - `Translation required before saving.` if the final payload still has no translation
- Right icon:
  - `variation + Plus` when the COR candidate meaning matches a saved wordbank entry
  - `Plus` otherwise

## Selection actions

### Selecting saved word row

- If row has linked add-variation candidate and is not already an exact saved variation:
  - triggers `onAddWordFromSearch(...)` using linked COR variant metadata + search seed
  - closes dialog only on successful add
- If that linked add-variation candidate is translation-gated, selecting the row opens the already-saved meaning / lemma instead of attempting the add.
- Otherwise:
  - opens existing saved meaning (`onOpenWordbankMeaning`) when `meaning_id` exists
  - else opens lemma page (`onOpenWordbankLemma`)
  - closes dialog immediately after opening

### Selecting COR row

- Always triggers `onAddWordFromSearch(...)` with `predictedStatus`:
  - `variation` when the COR candidate meaning matches a saved wordbank entry
  - `new` otherwise
- Exception: while translation is still loading, or after a no-translation final result, COR rows are disabled and do not fire save requests.
- Search-save payload keeps lemma translation and gloss separate:
  - `search_seed.english_translation` is populated only from the lemma translation
  - gloss/gloss translation remain disambiguation metadata and are not promoted into `english_translation`
- Saved search responses follow the same invariant:
  - `english_translation` remains the lemma translation
  - `gloss_translation` is returned separately when available
  - untranslated raw gloss is omitted from translation lines
- Dialog closes only when add succeeds.
- If the backend returns `saved_snapshot` with queued verification on the selected target:
  - the word page opens immediately from that snapshot,
  - shows `Verifying...` in the header,
  - and the open word page polls lemma details until Gemini returns a final result.
- For search-seed saves, the frontend still skips direct `/api/wordbank/lexemes/verify` and `/api/wordbank/lexemes/pronunciation` calls:
  backend background jobs perform the work and persist the result for the word page to pick up.
- The backend also enforces the translation gate:
  a search-seed save with empty or missing `search_seed.english_translation` returns `409`,
  so even stale or bypassed clients cannot save before translation generation completes.

### Selecting note or page row

- Selecting note calls `onOpenSavedNote(note.id)` and closes dialog.
- Selecting page item calls its navigation handler and closes dialog.

## Empty state and sections

- Empty state (`No results found.`) appears only when:
  - query is non-empty
  - and no wordbank, note, or page results exist
- Section order is fixed:
  1. Wordbank
  2. Notes
  3. Pages
- Separators are shown between present sections.

## Test coverage map for behavior

The search behavior above is validated by dedicated app-shell tests:

- Basics and minimum query behavior:
  - `frontend/src/test/app/app-shell-search-basics.test.tsx`
- Selection/action flow and COR caching/debounce:
  - `frontend/src/test/app/app-shell-search-actions.test.tsx`
- Error handling:
  - `frontend/src/test/app/app-shell-search-errors.test.tsx`
- Wordbank/Search semantic contract coverage:
  - `backend/tests/api/test_wordbank_add_and_list_endpoint.py`
  - `backend/tests/use_cases/test_wordbank_add_and_list.py`
  - frontend search hydration/polling tests consume typed fixtures from `frontend/src/test/app/wordbank-contract-fixtures.ts`
- Ranking/order:
  - `frontend/src/test/app/app-shell-search-ranking-order.test.tsx`
  - `frontend/src/test/app/app-shell-search-ranking-selection.test.tsx`
  - `frontend/src/test/app/app-shell-search-ranking-results.test.tsx`
  - `frontend/src/test/app/app-shell-search-ranking-state.test.tsx`
