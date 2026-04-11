# Typo-tolerant search

**Date:** 2026-04-11
**Status:** Approved

## Summary

When a search query returns no results in either the wordbank or COR lexicon, the backend computes Levenshtein-based suggestions and returns corrected results inline. The frontend shows a "Did you mean X?" item the user can select to replace their query.

---

## Architecture

### New

`backend/app/services/fuzzy_search.py`
- `levenshtein(a: str, b: str) -> int` — pure Wagner-Fischer DP
- `fuzzy_suggest(query: str, candidates: Iterable[str], *, max_distance: int = 2, max_results: int = 3) -> list[str]`
  - Pre-filters: `|len(query) - len(candidate)| <= max_distance` before computing Levenshtein
  - Returns candidates sorted by distance, then alphabetically

### Deleted

- `backend/app/services/typo/` — entire folder (7 modules + tests)
- `backend/app/bootstrap/runtime_typo.py`
- `backend/tests/services/test_typo_engine_unit.py`
- `backend/tests/services/test_typo_feature_extensive.py`
- `backend/tests/services/test_typo_ranking_decision_unit.py`

### Modified

**`token_classifier.py`**: remove `TypoEngine` import and `_new_with_typo_fallback` typo branch. Unknown tokens return `"new"` status. Token classification for corrected words still works — callers pass the corrected word as input.

**`app/main.py` / bootstrap**: remove `initialize_typo` call.

---

## Data flow

```
user types "huse"
  ├── GET /wordbank/search?query=huse
  │     ├── search_lemmas("huse") → 0 rows
  │     ├── fuzzy_suggest("huse", saved_wordbank_lemmas) → ["hus"]
  │     ├── search_lemmas("hus") → rows
  │     └── WordbankSearchResponse(items=[...], did_you_mean="hus")
  │
  └── GET /wordbank/search/cor-form?form=huse
        ├── lookup_form("huse") → 0 entries
        ├── fuzzy_suggest("huse", cor_unique_lemmas) → ["hus"]
        ├── lookup_form("hus") → entries
        └── CORSearchFormResponse(groups=[...], did_you_mean="hus")
```

COR unique lemmas: loaded once at `CORLocalLexiconService` init via `SELECT DISTINCT lemma FROM cor_entries WHERE norm = 'N'`, stored as `frozenset[str]`.

Fuzzy runs only when result set is empty. Max Levenshtein distance: 2.

---

## Schema changes

```python
# backend/app/api/schemas/v1/wordbank.py

class WordbankSearchResponse(BaseModel):
    items: list[WordbankSearchItem]
    did_you_mean: str | None = None  # NEW

class CORSearchFormResponse(BaseModel):
    groups: list[CORSearchGroup]
    did_you_mean: str | None = None  # NEW
```

---

## Backend changes

### `queries_lemmas.py` — `search_lemmas()`

```python
def search_lemmas(runtime, query, *, limit=8) -> WordbankSearchResponse:
    rows = runtime.repository.search_lemmas(normalized_query, limit=limit)
    if rows:
        return WordbankSearchResponse(items=[...])

    # Fuzzy fallback
    saved_lemmas = runtime.repository.list_all_lemma_strings()
    suggestions = fuzzy_suggest(normalized_query, saved_lemmas)
    if not suggestions:
        return WordbankSearchResponse(items=[])

    correction = suggestions[0]
    rows = runtime.repository.search_lemmas(correction, limit=limit)
    return WordbankSearchResponse(items=[...], did_you_mean=correction)
```

### `collaborators/cor_local.py` — `search_cor_form()`

Same pattern: if `entries` empty → `fuzzy_suggest(normalized_form, cor_local_lexicon_service.unique_lemmas)` → re-run with correction → return `did_you_mean`.

### `cor_local.py` — `CORLocalLexiconService`

Add `unique_lemmas: frozenset[str]` property, loaded lazily on first access via `SELECT DISTINCT lemma FROM cor_entries WHERE norm = 'N'`.

---

## Frontend changes

### `types-api.ts`

Add `did_you_mean?: string` to `WordbankSearchResponse` and `CORSearchFormResponse` types.

### `useSidebarSearch.ts`

- Track `didYouMean: string | null` state
- Set from first non-null `did_you_mean` found in either API response
- Clear when `normalizedQuery` changes to a non-empty value that returns real results
- Expose in return value

### `sidebar-search-results.tsx`

When `didYouMean` is non-null and `normalizedQuery !== didYouMean`, render at top of `CommandList`:

```tsx
<CommandItem
  value="did-you-mean-suggestion"
  onSelect={() => {
    actions.onSetSearchQuery(didYouMean)
  }}
>
  Did you mean "{didYouMean}"?
</CommandItem>
<CommandSeparator />
```

- Keyboard-navigable (down arrow selects, Enter triggers `onSelect`)
- `onSelect` calls `setSearchQuery(didYouMean)` — replaces typo with correction
- Results already shown below are for the corrected word (no extra fetch)

### `app-sidebar.tsx`

Wire `onSetSearchQuery` action through to `SidebarSearchResults`.

---

## API contract update

`docs/api-contract.md`: update `/api/wordbank/search` and `/api/wordbank/search/cor-form` response models to document `did_you_mean` field.

---

## Testing

### New

- `backend/tests/services/test_fuzzy_search.py` — levenshtein correctness, fuzzy_suggest ranking, length pre-filter
- `backend/tests/use_cases/test_wordbank_search_typo.py` — search returns `did_you_mean` + corrected items when query has no exact match; returns `None` when query has results; returns `None` when no correction found

### Removed

- `test_typo_engine_unit.py`
- `test_typo_feature_extensive.py`
- `test_typo_ranking_decision_unit.py`

### Extended

- `frontend/src/test/app/app-shell-search-basics.test.tsx` — typo banner renders, Enter on item replaces query
