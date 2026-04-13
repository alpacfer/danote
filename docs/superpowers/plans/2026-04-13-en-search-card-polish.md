# EN Search Card Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove ugly EN→DA badge + fallback texts from sentence search card; replace with minimal inline Languages icon in secondary text row, matching DA flow visual structure.

**Architecture:** Single component change in `sidebar-sentence-result.tsx`. Badge removed. "No Danish sentence available." + "No translation available." fallback strings removed. EN indicator moves inline into secondary text row as a `size-3` `Languages` icon prepended before muted secondary text.

**Tech Stack:** React 19, Tailwind v4, shadcn CommandItem, lucide-react `Languages` icon.

---

## File Map

- Modify: `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx` — remove Badge + fallbacks, add inline icon
- Modify: `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx` — update EN→DA assertions

---

### Task 1: Update `sidebar-sentence-result.tsx`

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx`

Current problems:
- `<Badge>` with `EN→DA` renders as first line → disrupts visual hierarchy
- `|| "No Danish sentence available."` → ugly fallback shown when `source_text` null
- `|| "No translation available."` → unnecessary fallback

Target: DA flow structure. EN indicator = small `Languages` icon inline in secondary row.

- [ ] **Step 1: Read file**

Run: `cat -n frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx`

Verify current shape matches known state (Badge at line 47, fallback strings at lines 24/29).

- [ ] **Step 2: Write updated component**

Replace full file content:

```tsx
import { Languages, Loader2, Plus } from "lucide-react"

import { formatSentenceTranslation, type SentenceSearchPreviewResponse } from "@/app/core"
import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"

type SidebarSentenceResultProps = {
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceSearchPreviewLoading: boolean
  onSaveSentence: (sourceText: string, englishTranslation: string | null) => Promise<void>
}

export function SidebarSentenceResult({
  sentenceSearchPreview,
  isSentenceSearchPreviewLoading,
  onSaveSentence,
}: SidebarSentenceResultProps) {
  const isBlocked = sentenceSearchPreview?.status === "blocked"
  const isSaveDisabled = isSentenceSearchPreviewLoading
    || sentenceSearchPreview === null
    || sentenceSearchPreview.source_text === null
    || isBlocked
  const displayText = sentenceSearchPreview?.source_text?.trim() ?? null
  const displayTranslation = formatSentenceTranslation(sentenceSearchPreview?.english_translation)
  const isEnglishQuery = sentenceSearchPreview?.query_language === "en"
  const secondaryText = sentenceSearchPreview?.message
    ? sentenceSearchPreview.message
    : (displayTranslation ?? null)

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          if (isSaveDisabled) return
          void onSaveSentence(
            sentenceSearchPreview.source_text,
            sentenceSearchPreview.english_translation,
          )
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-0.5">
          {displayText ? (
            <p className="line-clamp-2 text-sm font-semibold break-words">{displayText}</p>
          ) : null}
          {isSentenceSearchPreviewLoading ? (
            <Skeleton
              className="h-3 w-24 bg-accent group-data-[selected=true]/search-item:bg-accent-foreground/20"
              data-testid="sentence-search-translation-skeleton"
            />
          ) : secondaryText ? (
            <span className="text-muted-foreground text-xs leading-4 break-words flex items-center gap-1">
              {isEnglishQuery ? <Languages className="size-3 shrink-0" aria-label="Translated from English" /> : null}
              {secondaryText}
            </span>
          ) : null}
        </div>
        {isSentenceSearchPreviewLoading ? (
          <Loader2 className="text-muted-foreground size-4 shrink-0 animate-spin" />
        ) : (
          <Plus
            className={
              isSaveDisabled
                ? "text-muted-foreground/40 size-4 shrink-0"
                : "text-muted-foreground size-4 shrink-0"
            }
          />
        )}
      </CommandItem>
    </CommandGroup>
  )
}
```

Key changes:
- Removed `Badge` import + usage
- `displayText` uses `?? null` (no "No Danish sentence available." fallback)
- `secondaryText` uses `?? null` (no "No translation available." fallback)
- `displayText ? <p>...</p> : null` — no primary text if null
- `secondaryText ? <span>...</span> : null` — no secondary text if null
- `isEnglishQuery` → prepend `<Languages size-3>` inside secondary span
- Removed `Badge` from imports

- [ ] **Step 3: Run lint**

```bash
cd frontend && npx eslint src/app/chrome/sidebar/sidebar-sentence-result.tsx --max-warnings 0
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx
git commit -m "feat: move EN translation indicator inline, remove fallback strings"
```

---

### Task 2: Update tests for EN→DA assertions

**Files:**
- Modify: `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx`

Two tests currently assert `findByText("EN→DA")` — these must change to assert the `Languages` icon is present (via `aria-label`) and "EN→DA" text is gone.

- [ ] **Step 1: Read test file around EN tests (lines 543–615)**

```bash
sed -n '543,615p' frontend/src/test/app/app-shell-search-sentence-verification.test.tsx
```

Confirm lines 571 and 610 are the two `findByText("EN→DA")` assertions.

- [ ] **Step 2: Update test at line 543 — "shows an English-origin badge..."**

Rename test + update assertions. Replace the EN→DA assertion with icon check:

Old (line 571):
```tsx
expect(await within(dialog).findByText("EN→DA")).toBeInTheDocument()
```

New:
```tsx
expect(await within(dialog).findByLabelText("Translated from English")).toBeInTheDocument()
expect(within(dialog).queryByText("EN→DA")).not.toBeInTheDocument()
```

Also update test description from `"shows an English-origin badge, no raw-input underline, and saves the Danish preview"` to `"shows translated-from-English icon, no raw-input underline, and saves the Danish preview"`.

- [ ] **Step 3: Update test at line 590 — "shows a blocked English preview message..."**

Old (line 610):
```tsx
expect(await within(dialog).findByText("EN→DA")).toBeInTheDocument()
```

New:
```tsx
expect(await within(dialog).findByLabelText("Translated from English")).toBeInTheDocument()
expect(within(dialog).queryByText("EN→DA")).not.toBeInTheDocument()
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-sentence-verification.test.tsx
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/test/app/app-shell-search-sentence-verification.test.tsx
git commit -m "test: update EN search card assertions to inline icon"
```

---

### Task 3: Full verification

- [ ] **Step 1: Run full frontend test suite**

```bash
cd frontend && npx vitest run
```

Expected: all pass, no regressions.

- [ ] **Step 2: Run lint + maintainability check**

```bash
cd /home/alejandro/Documents/github/danote/danote && make lint && make maintainability-check
```

Expected: all pass.

- [ ] **Step 3: Final commit if needed**

Only if any fix-up changes were made.
