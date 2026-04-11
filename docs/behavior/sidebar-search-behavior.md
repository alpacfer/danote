# Sidebar search behavior

Exact behavior of sidebar command search ("Search words and notes...").

## Entry points and core modules

- UI shell/dialog: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`
- Query + API: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
- Ranking + de-dup: `frontend/src/app/chrome/sidebar/use-sidebar-search-ranking.ts`
- Result rendering: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`, `sidebar-wordbank-results.tsx`, `sidebar-cor-results.tsx`

## Open/close and input behavior

- Open via: sidebar "Search..." button, `Cmd/Ctrl+K`.
- Close → clears `searchQuery` + command selection override.
- Input normalized via `normalizeSearchWord(...)` before state update.
- Placeholder: `Search words and notes...`

## Data sources

1. **Saved wordbank** (backend search endpoint)
2. **COR form analyses** (backend COR endpoint, two-phase fetch)
3. **Saved notes** (local in-memory filter)
4. **Static pages** (Playground/Notes/Wordbank/Sentencebank/Developer)

### Notes filtering

- Non-empty `normalizedQuery` only. Matches `note.name` + `note.text` (case-insensitive `da-DK`). Limited to 8.

### Page filtering

- Empty query → all pages. Non-empty → filtered by case-insensitive `da-DK` includes on label.

## Saved wordbank API behavior

Endpoint: `GET /api/wordbank/search?query=<q>&limit=8`

- Debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`. Skipped when query length `< 2`.
- Cached by normalized query. Error/empty → empty matches.
- Sidebar keeps exact-ish rows only: `normalized lemma === normalizedQuery` or `normalized match_surface === normalizedQuery`; all others discarded.

## COR form API behavior

Endpoints:
- `GET /api/wordbank/search/cor-form?form=<q>&limit=100&include_translations=false`
- `GET /api/wordbank/search/cor-form?form=<q>&limit=100`

- Skipped when: empty query, whitespace present, `isShortLetterWord(...)`.
- Debounced by `SEARCH_RESOLVE_DEBOUNCE_MS`.
- Two-phase fetch: (1) partial payload without translations → render; (2) full payload with translations → replace.
- Phase 2 in-flight: `isCorTranslationsLoading=true`, skeleton placeholders, COR save rows disabled (loading skeletons, no extra locked copy).
- Full payload cached by normalized query.
- Translation fetch failure → toast error, partial results remain.
- Translation label normalization: content-word results drop frame scaffolding but may keep short multi-word phrases; function words keep minimal lexicalized context.

## Cache invalidation

`wordbankCacheVersion` or `searchTranslationConfigVersion` changes → clear wordbank cache + COR cache + reset displayed results asynchronously. Ensures new saves/edits reflected + translation provider changes force refetch.

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

- Primary title = `variant.form`. May show "from \<lemma\>" with translation in parentheses.
- Sense-level gloss translation = separate disambiguation text, not fallback English.
- During loading: skeleton placeholders for translation-dependent text.
- COR add rows disabled until `saveable_translation` available. Shows `Translation required before saving.` if final payload lacks it.
- Right icon: `variation + Plus` (meaning matches saved entry), `Plus` otherwise.

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

### Selecting note or page row

- Note → `onOpenSavedNote(note.id)` + close.
- Page → navigation handler + close.

## Empty state and sections

- "No results found." only when: query non-empty AND no wordbank/note/page results.
- Section order: (1) Wordbank, (2) Notes, (3) Pages. Separators between present sections.

## Test coverage map

- Basics/minimum query: `frontend/src/test/app/app-shell-search-basics.test.tsx`
- Actions/COR caching/debounce: `frontend/src/test/app/app-shell-search-actions.test.tsx`
- Error handling: `frontend/src/test/app/app-shell-search-errors.test.tsx`
- Wordbank/search contract: `backend/tests/api/test_wordbank_add_and_list_endpoint.py`, `backend/tests/use_cases/test_wordbank_add_and_list.py`, `frontend/src/test/app/wordbank-contract-fixtures.ts`
- Ranking/order: `frontend/src/test/app/app-shell-search-ranking-order.test.tsx`, `app-shell-search-ranking-selection.test.tsx`, `app-shell-search-ranking-results.test.tsx`, `app-shell-search-ranking-state.test.tsx`
