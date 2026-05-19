# Sidebar search behavior

Exact behavior of sidebar command search ("Search words...").

## Entry points and core modules

- UI shell/dialog: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`
- Query + API: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
- Ranking + de-dup: `frontend/src/app/chrome/sidebar/use-sidebar-search-ranking.ts`
- Result rendering: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`, `sidebar-wordbank-results.tsx`, `sidebar-cor-results.tsx`

## Open/close and input behavior

- Open via: sidebar "Search..." button, `Cmd/Ctrl+K`.
- Close → clears `searchQuery` + command selection override.
- Input keeps the raw typed value so spaces survive while composing a sentence query. Normalization happens downstream in `useSidebarSearch`.
- Placeholder: `Search words...`
- Single-word queries render a generic `Searching` skeleton group as soon as wordbank/COR/English lookup starts, including during debounce. Once the flow shape is known, those generic rows give way to source-specific results or source-specific skeleton rows.

## Data sources

1. **Saved wordbank** (backend search endpoint)
2. **COR form analyses** (backend COR endpoint, two-phase fetch)
3. **English local dictionary** (single-token EN form endpoint, then translated COR lookup)
4. **Static pages** (Wordbank/Sentencebank/Developer)
5. **Sentence mode** (multi-word sentence preview with Danish-first save)

## Sentence mode

- Trigger: normalized query contains 2 or more whitespace-delimited words.
- Number-only queries are excluded from sentence mode and use the Numbers page
  result only; mixed number+word queries still use normal sentence mode.
- Preview endpoint: `POST /api/sentencebank/search-preview`.
- Result set: exactly one row under `Sentence`.
- While sentence mode is active, sidebar suppresses saved-word, COR, and page groups.
- Sentence mode owns the result area immediately and shows the sentence loading row during debounce/request gaps; generic `No results found.` is never shown for an in-progress sentence query.
- Sidebar uses adaptive debounce before sentence preview: 200 ms for heuristic Danish queries, 350 ms for heuristic English/unknown queries.
- After that debounce, sidebar fires two sentence-preview requests in parallel for the same normalized query:
  - `fast: true` for immediate preview feedback
  - `fast: false` for the final verified result
- Only the full result is cached per normalized query. The fast result is transient UI state.
- Preview requests receive whitespace-normalized sentence text with the user's capitalization preserved.
- Danish and unknown-language queries stay in Danish-first flow: the fast result skips verification and the full result verifies the typed sentence, uses corrected Danish text when available, then returns the English translation for that finalized Danish sentence.
- Explicit English queries switch flow: the fast result uses heuristic language detection plus translation only, and the full result translates the corrected or normalized English sentence to Danish without a second Danish verification pass.
- English-origin previews render without a visible translation indicator or helper row.
- Input underline overlay only appears for non-English previews with verification errors. English-origin queries do not underline the raw English input.
- Sentence translation display is sentence-cased; the UI no longer lowercases translation text.
- Sentence verification corrections preserve initial capitalization and must not append a trailing period unless the source already has one.
- English queries that cannot be translated to Danish return a blocked sentence row with an inline message and disabled save action.
- Save action: `POST /api/sentencebank/sentences`, then close dialog.
- Successful sentence save increments both `sentencebankRefreshTick` and `wordbankRefreshTick` because sentence save now mutates both stores.

### Page filtering

- Empty query → all pages. Non-empty → filtered by case-insensitive `da-DK` includes on label.

## Saved wordbank API behavior

Endpoint: `GET /api/wordbank/search?query=<q>&limit=8`

- Debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`. Skipped when query length `< 2`,
  sentence mode is active, or the query is number-only.
- Cached by normalized query. Error/empty → empty matches.
- Sidebar keeps exact-ish rows only: `normalized lemma === normalizedQuery` or `normalized match_surface === normalizedQuery`; all others discarded.
- Static presaved words (pronouns, function words, calendar/time words, and
  number words represented as saved defaults) are returned by the backend before
  COR or provider translation. Selecting a saved static row opens the raw lemma
  word page; it does not route to the owning pinned tab. Numeric-only page
  results still open the Numbers & Time pinned page.

## COR form API behavior

Endpoints:
- `GET /api/wordbank/search/cor-form?form=<q>&limit=100&include_translations=false`
- `GET /api/wordbank/search/cor-form?form=<q>&limit=100`
- `GET /api/wordbank/search/cor-form?form=<da>&en_query=<en>`
- `POST /api/wordbank/search/cor-form-batch`

- Skipped when: empty query, whitespace present, `isShortLetterWord(...)`,
  sentence mode is active, or the query is number-only.
- Debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`.
- Two-phase fetch: (1) partial payload without translations → render; (2) full payload with translations → replace.
- Phase 2 in-flight: `isCorTranslationsLoading=true`, skeleton placeholders, COR save rows disabled (loading skeletons, no extra locked copy).
- Full payload cached by normalized query.
- Translation fetch failure → toast error, partial results remain.
- Translation label normalization: content-word results drop frame scaffolding but may keep short multi-word phrases; function words keep minimal lexicalized context.
- `en_query` narrows all returned COR groups through Gemini meaning-match selection. If Gemini returns no usable match or fails, all groups remain visible.

## English form API behavior

Endpoint: `GET /api/wordbank/search/en-form?form=<q>&include_translations=true`

- Skipped when: sentence mode, number-only query, empty query, length `< 2`, whitespace present, or `isShortLetterWord(...)`.
- Debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`.
- Uses the local English dictionary only; it does not run COR lookup, Danish classification, or `/resolve-query`.
- Full payload cached by normalized query, including empty `groups`.
- English inflected/surface forms are translated before falling back to lemma translation, so a query like `dogs` can resolve to Danish `hunde` and then to the COR lemma `hund`.
- For groups with a Danish translation, sidebar looks up the translated Danish form in COR and prefers any matching COR-backed rows.
- Translated English results use one batch COR request for all Danish translation keys; the backend returns item responses in the same order as requested.
- Groups without a matching COR row stay as generated non-COR fallback rows.
- When one English query has two or more distinct Danish translations, the backend asks Gemini once for short per-choice disambiguation labels and the sidebar shows those compact labels on both COR-backed and fallback rows.
- While English/COR translation lookup is loading, search first shows the generic `Searching` skeleton during English resolution. After untranslated COR candidate lookup determines the exact pending row count, the UI switches to the `Translated From English` section and renders that many placeholders until the translated payload arrives.

## Cache invalidation

`wordbankCacheVersion` or `searchTranslationConfigVersion` changes → clear wordbank cache + COR cache + sentence-preview cache + reset displayed results asynchronously. Ensures new saves/edits reflected + translation provider changes force refetch.

## Ranking and ordering

### Saved-wordbank rows

Sorted by score desc (then lemma locale sort, then meaning id):

1. exact saved variation (`isExactSaved`) → 520
2. lemma exact match → 480
3. linked variation form exact match → 400
4. `match_surface` exact match → 360
5. linked variation form contains query → 280
6. `match_surface` contains query → 240
7. lemma starts with query → 200
8. otherwise → 0

### COR groups

Sorted by best variant score per group:

- exact variation-add candidate matching saved entry → 400
- other variation-add candidate matching saved entry → 320
- exact form match → 240
- form prefix match → 160
- tie-break: group lemma locale compare (`da-DK`)

## De-duplication and visibility

- COR variants with `cor_id` in saved `query_cor_ids` → hidden.
- COR variants already linked as add-variation targets for saved result → hidden from standalone COR list.
- Prefix-only saved matches → hidden (sidebar keeps exact lemma/surface only).
- ASCII queries may resolve as both Danish and English. Direct COR rows stay visible when the Danish result has a non-self English translation (for example `bog` → `book`), and self-translated COR rows wait behind English resolution to avoid flashing loanword/no-op Danish rows.

## Row presentation

### Saved word rows

- Primary title precedence: (1) linked display variant form, (2) exact matched surface form, (3) `display_lemma`, (4) `lemma`.
- "from \<lemma\>" hint when linked lemma context exists.
- Translation text: `english_translation` alone, or `english_translation, gloss_translation` when both exist and differ. Raw `gloss` never appended.
- Second line hidden for exact saved-surface links without gloss.
- Badges: linked variant `gram_raw` when display variant used, else `pos_tag`/`morphology`.
- Right icon: `Eye` (open existing), `variation + Plus` (add-variation).
- Add-variation candidate but COR translation loading/no `saveable_translation` → falls back to opening saved entry, shows `Eye` + inline `Translation required before saving.` when final payload has no `saveable_translation`.

### COR rows

- Primary title = `variant.form`. May show `from <lemma>` when lemma context is useful.
- Direct Danish-search translations render as their own secondary line. When a translated gloss is available, it is appended on the same line after a comma, e.g. `mother, person`.
- COR-backed English translation rows hide English source text; they show only the Danish form, except inflected Danish forms still show `from <Danish lemma>` (for example `hunde from hund`).
- Sense-level gloss translation disambiguates the translation line, not fallback English.
- During loading: skeleton placeholders for translation-dependent text.
- COR add rows disabled until `saveable_translation` available. Shows `Translation required before saving.` if final payload lacks it.
- Right icon: `variation + Plus` (meaning matches saved entry), `Plus` otherwise.

### English fallback rows

- Primary title = Danish translation when available; otherwise English lemma.
- English source hints are hidden; fallback rows keep the Danish title and optional disambiguation only.
- Optional disambiguation label appears only when the backend returns one for a multi-translation English query.
- Rows without a Danish translation are disabled and show `Translation required before saving.`
- Right icon: `Plus` when saveable, muted `Plus` when disabled.

## Selection actions

### Selecting saved word row

- Linked add-variation candidate + not exact saved variation → `onAddWordFromSearch(...)` using COR variant metadata + search seed → close on success.
- Translation-gated candidate → opens saved meaning/lemma instead of add.
- Otherwise: `onOpenWordbankMeaning` (when `meaning_id` exists) or `onOpenWordbankLemma` → close immediately.

### Selecting COR row

- Always → `onAddWordFromSearch(...)` with `predictedStatus`: `variation` (matches saved entry) or `new`.
- Translation loading → COR rows disabled, no save request.
- Search-save payload keeps lemma translation, gloss translation, saveability separate:
  - `search_seed.english_translation` from backend `saveable_translation`
  - displayed parentheses from `lemma_translation` only
  - gloss/gloss translation = disambiguation metadata, not promoted to `lemma_translation`
  - primary provider framed lemma translation collapses to original Danish → treated as invalid → prefer Gemini contextual lemma translation
  - Gemini fallback: no gloss required; glossless entries send lemma/POS/morphology context; verbs framed as `at <infinitive>`
  - Gemini returns non-empty contextual translation → trusted even if English lemma matches Danish lemma text
  - no Gemini + no translated gloss → `lemma_translation` empty, translated gloss used as `saveable_translation` if available
  - neither available → row blocked, shows `Translation required before saving.`
- Saved search responses: `english_translation` = lemma translation, `gloss_translation` separate when available, untranslated raw gloss omitted.
- Close only on add success.
- Backend returns `saved_snapshot` with queued verification → word page opens immediately, shows `Verifying...`, polls lemma details until Gemini final result.
- Search-seed saves skip direct `/api/wordbank/lexemes/verify` + `/api/wordbank/lexemes/pronunciation`: backend background jobs do work, word page picks up.
- `queued_pronunciation_forms` in response → word page polls until pronunciation playable or timeout.
- Backend enforces translation gate: save blocked while translation loading, sidebar submits only when `saveable_translation` present.

### Selecting English fallback row

- Saveable fallback rows call `onAddWordFromSearch(...)` with a generated non-COR `search_seed`.
- `search_seed.lemma` and `surface` use the normalized Danish translation.
- `search_seed.dictionary_status = "generated_non_cor"`.
- `search_seed.english_translation` uses the original English query; `meaning_key` uses the English lemma and `gloss` uses the top English sense when present.
- Close only on add success.

### Selecting page row

- Page → navigation handler + close.

## Free-trial daily limit

- When the backend rejects a search lookup with HTTP `429`
  (`trial_daily_limit_reached`), the search dialog shows an amber banner above
  results: the user has spent the day's hosted-key searches.
- Signed-in free-trial users are capped per account. Guest users are capped per
  anonymous browser id, defaulting to 20 distinct words per day, while each
  guest session still gets a fresh empty wordbank/sentencebank workspace.
- The banner is keyed to the current search attempt (`searchAttemptKey` =
  `resetVersion:normalizedQuery`); editing the query or a config/cache reset
  clears it automatically — no manual dismissal.
- The banner's "Add your API keys" action closes search and navigates to the
  Account section. Words already searched earlier today still render (the
  backend treats a repeated word as free).
- Only the metered endpoints trigger this (`cor-form`, `cor-form-batch`,
  `en-form`); the cor/en search hooks detect `ApiRequestError.status === 429`.

## Empty state and sections

- "No results found." only when: query non-empty, no wordbank/page results, and no search lookup is still loading.
- Section order: (1) Wordbank, (2) Translated From English, (3) Pages. Separators between present sections.

## Test coverage map

- Basics/minimum query: `frontend/src/test/app/app-shell-search-basics.test.tsx`
- Actions/COR caching/debounce: `frontend/src/test/app/app-shell-search-actions.test.tsx`
- Error handling: `frontend/src/test/app/app-shell-search-errors.test.tsx`
- Sentence preview / English-origin behavior: `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx`
- Wordbank/search contract: `backend/tests/api/test_wordbank_add_and_list_endpoint.py`, `backend/tests/use_cases/test_wordbank_add_and_list.py`, `frontend/src/test/app/wordbank-contract-fixtures.ts`
- Ranking/order: `frontend/src/test/app/app-shell-search-ranking-order.test.tsx`, `app-shell-search-ranking-selection.test.tsx`, `app-shell-search-ranking-results.test.tsx`, `app-shell-search-ranking-state.test.tsx`
- Free-trial limit (banner + opt-in gate): `frontend/src/test/app/use-sidebar-cor-search-trial.test.ts`, `frontend/src/test/app/api-keys-gate.test.tsx`; backend `backend/tests/db/test_user_trial.py`, `backend/tests/use_cases/test_trial.py`, `backend/tests/api/test_account_trial.py`
