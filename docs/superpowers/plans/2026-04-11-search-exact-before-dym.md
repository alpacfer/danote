# Search: Exact Results Before Did-You-Mean

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder search results — exact/direct matches first, DYM banner middle, corrected-word results last.

**Architecture:** Expose `wordbankDidYouMean`/`corDidYouMean` separately from hook. Replace merged `didYouMean` in state type with both fields. Derive direct/corrected split in `SidebarSearchResults`. Render: direct group → DYM item → corrected group. Update `orderedCommandItemValues` to match new visual order.

**Tech Stack:** React 19, TypeScript, shadcn/ui Command

---

## File Map

- Modify: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` — expose both DYM fields from return
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` — update state type + render logic
- Modify: `frontend/src/app/chrome/sidebar/app-sidebar.tsx` — wire both DYM fields + update orderedCommandItemValues
- Modify: `frontend/src/test/app/mock-fetch.ts` — add `did_you_mean` to corSearchFormResponse option type
- Modify: `frontend/src/test/app/app-shell-search-basics.test.tsx` — add ordering test

---

## Task 1: Add `did_you_mean` to corSearchFormResponse mock type

**Files:**
- Modify: `frontend/src/test/app/mock-fetch.ts`

Current `corSearchFormResponse` option type (lines ~281-309) lacks `did_you_mean`. Add it so tests can simulate COR DYM.

- [ ] **Step 1: Read mock-fetch.ts lines 281-310**

Confirm current type definition location.

- [ ] **Step 2: Add `did_you_mean` to type**

In `mock-fetch.ts`, find the `corSearchFormResponse?:` block and add the field:

```typescript
  corSearchFormResponse?: {
    form: string
    did_you_mean?: string | null   // ADD THIS LINE
    groups: Array<{
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/test/app/mock-fetch.ts
git commit -m "test: add did_you_mean to corSearchFormResponse mock type"
```

---

## Task 2: Write failing test for DYM ordering

**Files:**
- Modify: `frontend/src/test/app/app-shell-search-basics.test.tsx`

Test: COR has exact results (no DYM) + wordbank has DYM → COR results appear BEFORE DYM banner in DOM.

- [ ] **Step 1: Add test**

Append to the `describe("App shell and search", ...)` block in `app-shell-search-basics.test.tsx`:

```typescript
  it("shows direct COR results before did-you-mean when wordbank has correction but COR has exact match", async () => {
    mockFetchImplementation({
      wordbankSearchHandler: async (_input) => {
        const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
        const parsed = new URL(url, "http://localhost")
        const query = parsed.searchParams.get("query") ?? ""
        if (query === "huse") {
          return responseOf({
            items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
            did_you_mean: "hus",
          })
        }
        return responseOf({ items: [] })
      },
      corSearchFormResponse: {
        form: "huse",
        did_you_mean: null,
        groups: [
          {
            lemma: "hus",
            gloss: "house",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.HUS.1",
                form: "huse",
                lemma: "hus",
                gloss: "houses",
                lemma_translation: "house",
                gram_raw: "sb.itk.pl.ubest",
                norm: "N",
                lemma_idx: 1,
                gram_code: 1,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Number=Plur|Definite=Ind",
                features: { Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    const searchButton = await screen.findByRole("button", { name: /search/i })
    fireEvent.click(searchButton)
    const commandDialog = await screen.findByRole("dialog")
    const input = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(input, { target: { value: "huse" } })

    const dymItem = await within(commandDialog).findByText(/did you mean/i)
    const corResult = await within(commandDialog).findByText(/huse/i)

    // COR result must appear before DYM banner in DOM
    expect(corResult.compareDocumentPosition(dymItem) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-basics.test.tsx --reporter=verbose
```

Expected: FAIL on the new test — DYM currently renders before COR results.

- [ ] **Step 3: Commit failing test**

```bash
git add frontend/src/test/app/app-shell-search-basics.test.tsx
git commit -m "test: add failing test for DYM ordering after direct results"
```

---

## Task 3: Expose wordbankDidYouMean + corDidYouMean from hook

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`

Currently returns merged `didYouMean = wordbankDidYouMean ?? corDidYouMean`. Expose both separately instead.

- [ ] **Step 1: Update return value**

In `use-sidebar-search.ts`, find the `return {` block (lines ~209-218) and replace:

```typescript
  return {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    didYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
  }
```

with:

```typescript
  return {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
  }
```

Also delete the merged `didYouMean` line (line ~34: `const didYouMean = wordbankDidYouMean ?? corDidYouMean`).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/chrome/sidebar/use-sidebar-search.ts
git commit -m "refactor: expose wordbankDidYouMean + corDidYouMean separately from useSidebarSearch"
```

---

## Task 4: Update SidebarSearchResultsState type

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`

Replace `didYouMean: string | null` with two fields.

- [ ] **Step 1: Update state type**

In `sidebar-search-results.tsx`, find `SidebarSearchResultsState` (lines ~32-41) and replace:

```typescript
export type SidebarSearchResultsState = {
  normalizedQuery: string
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasNoteResults: boolean
  hasPageResults: boolean
  didYouMean: string | null
}
```

with:

```typescript
export type SidebarSearchResultsState = {
  normalizedQuery: string
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasNoteResults: boolean
  hasPageResults: boolean
  wordbankDidYouMean: string | null
  corDidYouMean: string | null
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/chrome/sidebar/sidebar-search-results.tsx
git commit -m "refactor: split didYouMean into wordbankDidYouMean + corDidYouMean in SidebarSearchResultsState"
```

---

## Task 5: Wire both DYM fields in app-sidebar.tsx

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`

Replace `didYouMean` destructuring + state usage. Update `orderedCommandItemValues` to match new render order.

- [ ] **Step 1: Update hook destructuring**

In `app-sidebar.tsx`, find hook destructuring (lines ~92-104):

```typescript
  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    didYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
  } = useSidebarSearch({
```

Replace with:

```typescript
  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
  } = useSidebarSearch({
```

- [ ] **Step 2: Update searchResultState**

Find `const searchResultState: SidebarSearchResultsState = {` (lines ~211-219):

```typescript
  const searchResultState: SidebarSearchResultsState = {
    normalizedQuery,
    hasAnyResults,
    hasWordbankSectionResults,
    hasWordbankActions,
    hasNoteResults,
    hasPageResults,
    didYouMean,
  }
```

Replace with:

```typescript
  const searchResultState: SidebarSearchResultsState = {
    normalizedQuery,
    hasAnyResults,
    hasWordbankSectionResults,
    hasWordbankActions,
    hasNoteResults,
    hasPageResults,
    wordbankDidYouMean,
    corDidYouMean,
  }
```

- [ ] **Step 3: Update orderedCommandItemValues**

Find `const orderedCommandItemValues = useMemo(...)` (lines ~187-202). Replace body:

```typescript
  const orderedCommandItemValues = useMemo(() => {
    const values: string[] = []
    // Direct wordbank (no wordbank correction)
    if (!wordbankDidYouMean) {
      for (const item of orderedWordbankResults) {
        values.push(`wordbank-${savedWordbankResultKey(item)}`)
      }
    }
    // Direct COR (no COR correction)
    if (!corDidYouMean) {
      for (const variant of orderedCorVariantsToRender) {
        values.push(`cor-variant-${variant.cor_id}`)
      }
    }
    // DYM banner item
    if (wordbankDidYouMean || corDidYouMean) {
      values.push("did-you-mean-suggestion")
    }
    // Corrected wordbank
    if (wordbankDidYouMean) {
      for (const item of orderedWordbankResults) {
        values.push(`wordbank-${savedWordbankResultKey(item)}`)
      }
    }
    // Corrected COR
    if (corDidYouMean) {
      for (const variant of orderedCorVariantsToRender) {
        values.push(`cor-variant-${variant.cor_id}`)
      }
    }
    for (const note of matchingNotes) {
      values.push(`note-${note.id}`)
    }
    for (const page of matchingPageItems) {
      values.push(page.key)
    }
    return values
  }, [corDidYouMean, matchingNotes, matchingPageItems, orderedCorVariantsToRender, orderedWordbankResults, wordbankDidYouMean])
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chrome/sidebar/app-sidebar.tsx
git commit -m "feat: wire wordbankDidYouMean + corDidYouMean through app-sidebar"
```

---

## Task 6: Update SidebarSearchResults render logic

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`

Replace single DYM-at-top render with: direct group → DYM item → corrected group.

- [ ] **Step 1: Replace render function body**

Replace full `SidebarSearchResults` function (lines ~82-169) with:

```typescript
export function SidebarSearchResults({ state, data, actions }: SidebarSearchResultsProps) {
  const dymSuggestion = state.wordbankDidYouMean ?? state.corDidYouMean

  const hasDirectWordbank = !state.wordbankDidYouMean && data.orderedWordbankResults.length > 0
  const hasDirectCor = !state.corDidYouMean && data.corSearchVariantsToRender.length > 0
  const hasDirectResults = hasDirectWordbank || hasDirectCor

  const hasCorrectedWordbank = Boolean(state.wordbankDidYouMean) && data.orderedWordbankResults.length > 0
  const hasCorrectedCor = Boolean(state.corDidYouMean) && data.corSearchVariantsToRender.length > 0
  const hasCorrectedResults = hasCorrectedWordbank || hasCorrectedCor

  const hasWordbankSection = hasDirectResults || hasCorrectedResults

  return (
    <CommandList>
      {state.normalizedQuery && !state.hasAnyResults ? <CommandEmpty>No results found.</CommandEmpty> : null}

      {/* Direct results — exact query match */}
      {hasDirectResults ? (
        <CommandGroup heading="Wordbank">
          {hasDirectWordbank ? (
            <SidebarWordbankResults
              orderedWordbankResults={data.orderedWordbankResults}
              displayVariantBySavedResult={data.displayVariantBySavedResult}
              addVariationBySavedResult={data.addVariationBySavedResult}
              exactSavedVariationKeySet={data.exactSavedVariationKeySet}
              normalizedQuery={state.normalizedQuery}
              isTranslationsLoading={data.isCorTranslationsLoading}
              wordbankItemValue={data.wordbankItemValue}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onOpenWordbankLemma={actions.onOpenWordbankLemma}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
          {hasDirectCor ? (
            <SidebarCorResults
              orderedCorSearchGroups={data.orderedCorSearchGroups}
              corSearchVariantsToRender={data.corSearchVariantsToRender}
              variationCandidateCorIdSet={data.variationCandidateCorIdSet}
              normalizedQuery={state.normalizedQuery}
              corVariantItemValue={data.corVariantItemValue}
              isTranslationsLoading={data.isCorTranslationsLoading}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
        </CommandGroup>
      ) : null}

      {/* DYM banner — between direct and corrected */}
      {dymSuggestion ? (
        <>
          {hasDirectResults ? <CommandSeparator /> : null}
          <CommandItem
            value="did-you-mean-suggestion"
            onSelect={() => actions.onSetSearchQuery(dymSuggestion)}
          >
            Did you mean &quot;{dymSuggestion}&quot;?
          </CommandItem>
          {hasCorrectedResults ? <CommandSeparator /> : null}
        </>
      ) : null}

      {/* Corrected results — for the DYM suggestion word */}
      {hasCorrectedResults ? (
        <CommandGroup heading="Wordbank">
          {hasCorrectedWordbank ? (
            <SidebarWordbankResults
              orderedWordbankResults={data.orderedWordbankResults}
              displayVariantBySavedResult={data.displayVariantBySavedResult}
              addVariationBySavedResult={data.addVariationBySavedResult}
              exactSavedVariationKeySet={data.exactSavedVariationKeySet}
              normalizedQuery={state.normalizedQuery}
              isTranslationsLoading={data.isCorTranslationsLoading}
              wordbankItemValue={data.wordbankItemValue}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onOpenWordbankLemma={actions.onOpenWordbankLemma}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
          {hasCorrectedCor ? (
            <SidebarCorResults
              orderedCorSearchGroups={data.orderedCorSearchGroups}
              corSearchVariantsToRender={data.corSearchVariantsToRender}
              variationCandidateCorIdSet={data.variationCandidateCorIdSet}
              normalizedQuery={state.normalizedQuery}
              corVariantItemValue={data.corVariantItemValue}
              isTranslationsLoading={data.isCorTranslationsLoading}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
        </CommandGroup>
      ) : null}

      {(hasWordbankSection || state.hasWordbankActions) && state.hasNoteResults ? <CommandSeparator /> : null}
      {state.hasNoteResults ? (
        <CommandGroup heading="Notes">
          {data.matchingNotes.map((note) => (
            <CommandItem
              key={`search-note-${note.id}`}
              value={`note-${note.id}`}
              onSelect={() => {
                actions.onOpenSavedNote(note.id)
                actions.onCloseSearch()
              }}
              className="flex-col items-start gap-0.5"
            >
              <span className="font-medium">{note.name}</span>
              <span className="text-muted-foreground line-clamp-2 text-xs">
                {previewText(note.text, 80)}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      ) : null}
      {(hasWordbankSection || state.hasWordbankActions || state.hasNoteResults) && state.hasPageResults ? <CommandSeparator /> : null}
      {state.hasPageResults ? (
        <CommandGroup heading="Pages">
          {data.matchingPageItems.map((item) => {
            const Icon = item.icon
            return (
              <CommandItem
                key={item.key}
                value={item.key}
                onSelect={() => {
                  item.onSelect()
                  actions.onCloseSearch()
                }}
              >
                <Icon />
                <span>{item.label}</span>
                <CommandShortcut>{item.shortcut}</CommandShortcut>
              </CommandItem>
            )
          })}
        </CommandGroup>
      ) : null}
    </CommandList>
  )
}
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-basics.test.tsx --reporter=verbose
```

Expected: all tests pass including new ordering test.

- [ ] **Step 3: Run full frontend test suite**

```bash
cd frontend && npx vitest run --reporter=verbose
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chrome/sidebar/sidebar-search-results.tsx
git commit -m "feat: render direct results before did-you-mean banner in search"
```

---

## Task 7: Lint + verify

- [ ] **Step 1: Lint**

```bash
make lint
```

Expected: no errors.

- [ ] **Step 2: Full test suite**

```bash
make test
```

Expected: all pass.

- [ ] **Step 3: Final commit if any lint fixes needed**

```bash
git add -p
git commit -m "fix: lint issues from DYM reorder"
```
