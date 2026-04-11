# Card UI Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all card surfaces via shadcn `Card` + new `variant="subtle"`. Visual changes → edit only `card.tsx`.

**Architecture:** Add `variant` prop to `Card` via `cva` (already installed). Replace raw bordered `div`/`li` with `<Card variant="subtle">` across 6 files. Fix 2 `rounded-lg` mismatches on interactive surfaces inside cards.

**Tech Stack:** React 19, Tailwind CSS v4, shadcn/ui, class-variance-authority (already installed).

---

## Card inventory (established by research)

### Currently using `<Card>` (shadcn)
| File | Usage |
|------|-------|
| `notes-section.tsx` | `<Card p-0>` + inner `<button rounded-lg>` ← **button radius wrong** |
| `sentencebank-section.tsx` | `<Card><CardContent>` — clean |
| `wordbank-meaning-sections.tsx` | `<Card py-5><CardContent>` — clean |
| `wordbank-related-words.tsx` | outer `<Card>` clean; inner `<Button rounded-lg border>` ← **radius wrong** |
| `wordbank-verification-popover.tsx` | `VerificationReviewRow` uses `<Card className="gap-0 py-0 shadow-none">` — subtle pattern hardcoded |
| `developer-section.tsx` | outer `<Card>` clean; inner API status `<div rounded-xl border p-2>` ← needs Card |

### Raw bordered containers (→ `<Card>`)
| File | Current class | Target |
|------|--------------|--------|
| `wordbank-variation-grid.tsx` | `div rounded-xl border bg-muted/30 p-3 dark:bg-muted/15` | `<Card variant="subtle" className="bg-muted/30 p-3 dark:bg-muted/15">` |
| `wordbank-verification-popover.tsx` | `div rounded-xl border border-border/70 px-3 py-2` (action items inside VerificationReviewRow) | `<Card variant="subtle" className="px-3 py-2 border-border/70">` |
| `wordbank-lemma-header.tsx` | `div rounded-xl border border-border/70 p-5` (loading skeleton) | `<Card className="py-5"><CardContent className="space-y-3">` |
| `developer-probe-result.tsx` | `div rounded-xl border p-2 text-sm` | `<Card variant="subtle" className="p-2 text-sm">` |
| `developer-section.tsx` | `div rounded-xl border p-2` (API status items) | `<Card variant="subtle" className="p-2">` |
| `playground-header-actions.tsx` | `li rounded-xl border px-3 py-2` | `<li><Card variant="subtle" className="px-3 py-2">` |

### Search results — no changes needed
`CommandItem` in `sidebar-cor-results.tsx` and `sidebar-wordbank-results.tsx` are Command overlay list items, not card surfaces.

---

## Task 1: Fix `rounded-lg` on interactive surfaces inside cards

**Files:**
- Modify: `frontend/src/app/sections/notes-section.tsx:25`
- Modify: `frontend/src/app/sections/wordbank/wordbank-related-words.tsx:135`

**Why:** Parent `<Card>` is `rounded-xl`. Inner button with `rounded-lg` → visible corner gap on hover where card background bleeds through.

- [ ] **Step 1: Fix notes card button radius**

In `frontend/src/app/sections/notes-section.tsx`, change line 25:

```tsx
// Before
className="hover:bg-accent/60 focus-visible:ring-ring w-full rounded-lg p-4 text-left outline-none transition-colors hover:cursor-pointer focus-visible:ring-2"

// After
className="hover:bg-accent/60 focus-visible:ring-ring w-full rounded-xl p-4 text-left outline-none transition-colors hover:cursor-pointer focus-visible:ring-2"
```

- [ ] **Step 2: Fix related word candidate variant button radius**

In `frontend/src/app/sections/wordbank/wordbank-related-words.tsx`, change line 135:

```tsx
// Before
className="bg-muted/35 hover:bg-accent/60 h-auto w-full items-start justify-between rounded-lg border px-3 py-2 text-left"

// After
className="bg-muted/35 hover:bg-accent/60 h-auto w-full items-start justify-between rounded-xl border px-3 py-2 text-left"
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/sections/notes-section.tsx \
        frontend/src/app/sections/wordbank/wordbank-related-words.tsx
git commit -m "fix: align inner button radius to card rounded-xl"
```

---

## Task 2: Add `variant="subtle"` to the `Card` component

**Files:**
- Modify: `frontend/src/components/ui/card.tsx`

**`variant="subtle"`:** Same corners + border as default. No shadow, no default padding, no child gap. Background transparent (inherits or set via `className`). Callers set own padding.

Default Card: `rounded-xl border py-6 gap-6 shadow-sm bg-card text-card-foreground flex flex-col`

`variant="subtle"` strips: `py-6`→`py-0`, `gap-6`→`gap-0`, `shadow-sm`→`shadow-none`

- [ ] **Step 1: Replace the Card function with a cva-based version**

Rewrite `frontend/src/components/ui/card.tsx` to:

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const cardVariants = cva(
  "bg-card text-card-foreground flex flex-col rounded-xl border",
  {
    variants: {
      variant: {
        default: "gap-6 py-6 shadow-sm",
        subtle: "gap-0 py-0 shadow-none",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

type CardProps = React.ComponentProps<"div"> & VariantProps<typeof cardVariants>

function Card({ className, variant, ...props }: CardProps) {
  return (
    <div
      data-slot="card"
      className={cn(cardVariants({ variant }), className)}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("leading-none font-semibold", className)}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-6", className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-6 [.border-t]:pt-6", className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. Existing `<Card>` usages intact — `variant` defaults to `"default"`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/card.tsx
git commit -m "feat: add variant=subtle to Card component"
```

---

## Task 3: Standardize `VerificationReviewRow` to use `variant="subtle"`

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`

Component hardcodes `className="gap-0 py-0 shadow-none"`. Task 2 formalized this. Now clean up.

- [ ] **Step 1: Switch to `variant="subtle"`**

In `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`, find `VerificationReviewRow` body (~line 188):

```tsx
// Before
<Card className="gap-0 py-0 shadow-none">
  <CardContent className="space-y-3 px-3 py-3">

// After
<Card variant="subtle">
  <CardContent className="space-y-3 px-3 py-3">
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx
git commit -m "refactor: use Card variant=subtle in VerificationReviewRow"
```

---

## Task 4: Convert verification suggested-action items to `<Card variant="subtle">`

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`

Suggested-action items are raw `<div className="rounded-xl border border-border/70 px-3 py-2">` inside `VerificationReviewRow`.

- [ ] **Step 1: Replace raw div with `<Card variant="subtle">`**

In `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`, inside `VerificationReviewRow` (~lines 204–207):

```tsx
<div
  key={`${target.key}-${action.action_type}-${index}`}
  className="rounded-xl border border-border/70 px-3 py-2"
>
  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
```

Replace with:

```tsx
<Card
  key={`${target.key}-${action.action_type}-${index}`}
  variant="subtle"
  className="px-3 py-2 border-border/70"
>
  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
```

Also change closing `</div>` → `</Card>` for the outer element.

- [ ] **Step 2: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx
git commit -m "refactor: use Card variant=subtle for verification action items"
```

---

## Task 5: Convert variation grid cells to `<Card variant="subtle">`

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx`

Cells use raw `<div>` with `cn("rounded-xl border bg-muted/30 p-3 dark:bg-muted/15")`. Remove `cn()` import if unused after change.

- [ ] **Step 1: Import Card and replace div**

In `frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx`:

Add `Card` to import from `@/components/ui/card`:
```tsx
import { Card } from "@/components/ui/card"
```

Replace raw div (~lines 104–111):

```tsx
// Before
<div
  key={form.form}
  className={cn(
    "rounded-xl border bg-muted/30 p-3 dark:bg-muted/15",
  )}
>

// After
<Card
  key={form.form}
  variant="subtle"
  className="bg-muted/30 p-3 dark:bg-muted/15"
>
```

Change closing `</div>` → `</Card>`. Remove `cn` import if no other `cn(` usages remain.

- [ ] **Step 2: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx
git commit -m "refactor: use Card variant=subtle for variation grid cells"
```

---

## Task 6: Convert loading skeleton containers to `<Card>`

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx`

`WordbankDetailsLoadingSkeleton` renders placeholder containers mocking meaning cards (`<Card className="py-5">`). Make them real Cards.

- [ ] **Step 1: Import Card and CardContent**

In `frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx`, confirm or add:
```tsx
import { Card, CardContent } from "@/components/ui/card"
```

- [ ] **Step 2: Replace raw divs in the skeleton**

In `WordbankDetailsLoadingSkeleton` (~lines 204–222):

```tsx
<div
  key={`wordbank-details-loading-card-${item}`}
  data-testid="wordbank-details-loading-card"
  className="space-y-3 rounded-xl border border-border/70 p-5"
>
  <div className="flex flex-wrap items-center gap-2">
    <Skeleton className="h-5 w-6 rounded-full" />
    <Skeleton className="h-6 w-28" />
    <Skeleton className="h-5 w-16 rounded-full" />
    <Skeleton className="h-5 w-20 rounded-full" />
  </div>
  <Skeleton className="h-4 w-44" />
  <div className="space-y-2">
    <Skeleton className="h-4 w-32" />
    <Skeleton className="h-4 w-40" />
    <Skeleton className="h-4 w-36" />
  </div>
</div>
```

Replace with:

```tsx
<Card
  key={`wordbank-details-loading-card-${item}`}
  data-testid="wordbank-details-loading-card"
  className="py-5 border-border/70"
>
  <CardContent className="space-y-3">
    <div className="flex flex-wrap items-center gap-2">
      <Skeleton className="h-5 w-6 rounded-full" />
      <Skeleton className="h-6 w-28" />
      <Skeleton className="h-5 w-16 rounded-full" />
      <Skeleton className="h-5 w-20 rounded-full" />
    </div>
    <Skeleton className="h-4 w-44" />
    <div className="space-y-2">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-4 w-36" />
    </div>
  </CardContent>
</Card>
```

- [ ] **Step 3: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx
git commit -m "refactor: use Card for loading skeleton containers in lemma header"
```

---

## Task 7: Convert developer section inner items to `<Card variant="subtle">`

**Files:**
- Modify: `frontend/src/app/sections/developer-probe-result.tsx`
- Modify: `frontend/src/app/sections/developer-section.tsx`

- [ ] **Step 1: Fix `developer-probe-result.tsx`**

Add Card import:
```tsx
import { Card } from "@/components/ui/card"
```

Find (line 14):
```tsx
<div aria-label={ariaLabel} className="rounded-xl border p-2 text-sm">
```

Replace with:
```tsx
<Card aria-label={ariaLabel} variant="subtle" className="p-2 text-sm">
```

Change closing `</div>` → `</Card>`.

- [ ] **Step 2: Fix `developer-section.tsx` API status items**

In `frontend/src/app/sections/developer-section.tsx`, Card already imported.

Find (~line 129):
```tsx
<div key={item.name} className="rounded-xl border p-2">
```

Replace with:
```tsx
<Card key={item.name} variant="subtle" className="p-2">
```

Change closing `</div>` → `</Card>`.

- [ ] **Step 3: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/sections/developer-probe-result.tsx \
        frontend/src/app/sections/developer-section.tsx
git commit -m "refactor: use Card variant=subtle for developer section items"
```

---

## Task 8: Convert notification list items to `<Card variant="subtle">`

**Files:**
- Modify: `frontend/src/app/sections/playground-header-actions.tsx`

Notification items are `<li>` with card styling. `<Card>` renders `<div>`, so nest inside `<li>` to preserve semantic list structure.

- [ ] **Step 1: Import Card**

In `frontend/src/app/sections/playground-header-actions.tsx`, add `Card` to import from `@/components/ui/card`:
```tsx
import { Card } from "@/components/ui/card"
```

- [ ] **Step 2: Wrap list item content in Card**

Find (~lines 85–95):
```tsx
<li key={notification.id} className="rounded-xl border px-3 py-2">
  <div className="flex items-center justify-between gap-2">
    <p className="text-sm">{notification.message}</p>
    {!notification.read ? <Badge variant="secondary">New</Badge> : null}
  </div>
  <p className="text-muted-foreground mt-1 text-xs">
    {formatSavedNoteTimestamp(notification.createdAt)}
  </p>
</li>
```

Replace with:
```tsx
<li key={notification.id}>
  <Card variant="subtle" className="px-3 py-2">
    <div className="flex items-center justify-between gap-2">
      <p className="text-sm">{notification.message}</p>
      {!notification.read ? <Badge variant="secondary">New</Badge> : null}
    </div>
    <p className="text-muted-foreground mt-1 text-xs">
      {formatSavedNoteTimestamp(notification.createdAt)}
    </p>
  </Card>
</li>
```

- [ ] **Step 3: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/sections/playground-header-actions.tsx
git commit -m "refactor: use Card variant=subtle for notification list items"
```

---

## Task 9: Final verification

- [ ] **Step 1: Run full lint and type check**

```bash
cd /path/to/danote && make lint
```

Expected: no errors or warnings.

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all pass. Card changes purely structural/visual — no logic touched.

- [ ] **Step 3: Verify no raw `rounded-xl border` bordered containers remain outside `<Card>`**

```bash
grep -rn "rounded-xl border\|rounded-lg border\|rounded-md border" frontend/src/app/sections/ frontend/src/app/chrome/ --include="*.tsx"
```

Expected: only `rounded-xl border` inside shadcn primitives or ButtonGroup. Zero card-like `div`/`li` surfaces.

- [ ] **Step 4: Final commit if fixes needed**

```bash
git add -p
git commit -m "fix: resolve any remaining raw bordered container issues"
```

---

## After this plan: future design changes

Plan complete → card design changes:
1. **All cards:** edit `card.tsx` — change `rounded-xl`, add `ring`, change border, etc.
2. **Main cards only:** edit `"default"` branch of `cardVariants`
3. **Subtle/embedded only:** edit `"subtle"` branch
4. **Global radius:** change `--radius` in `index.css` — all `rounded-xl` (`calc(var(--radius) + 4px)`) update automatically