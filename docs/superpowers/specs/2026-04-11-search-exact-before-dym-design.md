# Search: exact results before did-you-mean

## Goal

Reorder search results so exact matches show first, did-you-mean (DYM) banner in middle, corrected-word results below.

## Current behavior

`didYouMean = wordbankDYM ?? corDYM`. DYM banner renders at top of `CommandList`, before all results. Confusing when COR has exact-form results — DYM appears above the exact hits.

## Desired layout

```
[direct wordbank results]   ← wordbankDYM == null
[direct COR results]        ← corDYM == null
─────────────────────────
Did you mean "X"?           ← DYM banner (if any DYM set)
─────────────────────────
[corrected wordbank results] ← wordbankDYM != null
[corrected COR results]      ← corDYM != null
```

If no DYM → no banner, all results show as now.
If all results are corrected (no direct) → results show above banner anyway (banner at bottom).

## Architecture

### 1. `use-sidebar-search.ts`

Expose `wordbankDidYouMean` + `corDidYouMean` separately (already computed, just not returned). Return both from hook instead of merged `didYouMean`.

### 2. `app-sidebar.tsx`

Replace `didYouMean` usage with `wordbankDidYouMean` + `corDidYouMean`. Pass both to `SidebarSearchResultsState`.

### 3. `SidebarSearchResultsState` (in `sidebar-search-results.tsx`)

Replace `didYouMean: string | null` with:
- `wordbankDidYouMean: string | null`
- `corDidYouMean: string | null`

### 4. `useSidebarSearchRanking`

No change. Ranking already scores by `normalizedQuery`. Direct results score higher (exact match scoring). Corrected results score lower or are for a different lemma. But ranking doesn't need to know about DYM — split happens at render time.

### 5. `SidebarSearchResults` render order

```
direct wordbank items   (orderedWordbankResults where lemma/surface === normalizedQuery, or all if wordbankDYM null)
direct COR groups       (orderedCorSearchGroups when corDYM null)
─── separator ───       (only if any DYM + any results above)
DYM banner              (if wordbankDYM || corDYM)
─── separator ───       (only if corrected results follow)
corrected wordbank      (orderedWordbankResults when wordbankDYM set)
corrected COR groups    (orderedCorSearchGroups when corDYM set)
```

Split wordbank results into direct vs corrected:
- `directWordbankResults` = items where `normalizeSearchWord(item.lemma) === normalizedQuery || normalizeSearchWord(item.match_surface) === normalizedQuery`
- `correctedWordbankResults` = remaining items (lemma/surface match correction, not original query)

Note: when `wordbankDYM == null`, all items are direct. When `wordbankDYM != null`, all items are corrected (backend only returns corrected items when DYM set).

### 6. `orderedCommandItemValues` in `app-sidebar.tsx`

Update to reflect new visual order: direct wordbank → direct COR → corrected wordbank → corrected COR → notes → pages.

## Scope

Frontend only. No backend changes. No schema changes. No ranking hook changes.

Files touched:
- `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
- `frontend/src/app/chrome/sidebar/app-sidebar.tsx`
- `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`

## Tests

Existing frontend search tests cover DYM rendering. Add/update tests:
- DYM banner renders below direct results, not above
- When no direct results exist, DYM banner still renders (at top of results)
- Both direct + corrected groups render when DYM set
