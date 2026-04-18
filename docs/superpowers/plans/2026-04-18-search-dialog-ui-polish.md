# Search Dialog UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish search dialog UI — softer item corners, remove hard separator line between input and results, improve character counter from raw text to styled badge.

**Architecture:** Two-file change. `command.tsx` handles primitive styling (item radius, input separator). `sidebar-search-input.tsx` handles counter badge. No new components, no new files.

**Tech Stack:** Tailwind CSS v4, shadcn/ui cmdk primitives, React 19.

---

## Current issues

| Issue | Location | Current | Problem |
|-------|----------|---------|---------|
| Item corners | `CommandItem` in `command.tsx:189` | `rounded-sm` | Too sharp, inconsistent with `rounded-xl` dialog |
| Separator | `CommandInput` wrapper in `command.tsx:91` | `border-b` | Hard visual cut, feels old |
| Counter | `sidebar-search-input.tsx:167-180` | Plain text `45/300` | Looks injected, not designed |

---

## File Map

- Modify: `frontend/src/components/ui/command.tsx` (items radius + input separator)
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-input.tsx` (counter badge)

---

### Task 1: Soften item corner radius

**Files:**
- Modify: `frontend/src/components/ui/command.tsx:189`

- [ ] **Step 1: Change `rounded-sm` → `rounded-md` in `CommandItem`**

In `command.tsx`, `CommandItem` className (line ~189):

```tsx
// Before
"group/search-item data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground [&_svg:not([class*='text-'])]:text-muted-foreground relative flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-hidden select-none data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",

// After
"group/search-item data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground [&_svg:not([class*='text-'])]:text-muted-foreground relative flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-hidden select-none data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
```

- [ ] **Step 2: Verify dev server renders rounded items**

Run: `make dev` (or ensure already running), open search dialog, check items have softer corners.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all pass (no test covers border-radius directly, regression check)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/command.tsx
git commit -m "style(search): soften command item corner radius sm→md"
```

---

### Task 2: Replace hard input separator with subtle spacer

**Files:**
- Modify: `frontend/src/components/ui/command.tsx:88-122`

The `CommandInput` wrapper div currently has `border-b px-3`. Goal: replace hard border with a subtle `border-b border-border/30` — keeps faint visual hint without the full-weight cut. Alternatively if user prefers zero line, we use `pb-2` only.

- [ ] **Step 1: Soften the separator**

In `command.tsx`, `CommandInput` function, the wrapper div (line ~91):

```tsx
// Before
<div
  data-slot="command-input-wrapper"
  className="flex h-9 items-center gap-2 border-b px-3"
>

// After
<div
  data-slot="command-input-wrapper"
  className="flex h-9 items-center gap-2 border-b border-border/30 px-3"
>
```

> Note: `border-border/30` uses 30% opacity of the border token — subtle visual hint, not a hard line. If user prefers zero line, use `pb-1` instead and remove `border-b border-border/30` entirely.

- [ ] **Step 2: Verify visually**

Open search dialog. Input/results transition should feel seamless, not cut.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/command.tsx
git commit -m "style(search): soften input/results separator to 30% opacity"
```

---

### Task 3: Style character counter as badge

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-input.tsx:166-181`

Current counter renders raw text. Replace with a pill badge using `bg-muted` background so it reads as a UI element, not injected text.

- [ ] **Step 1: Replace raw text span with badge span**

In `sidebar-search-input.tsx`, the `suffix` prop (lines ~166-181):

```tsx
// Before
suffix={shouldShowCounter ? (
  <span
    className={cn(
      "text-muted-foreground inline-flex h-4 items-center justify-end text-[10px] leading-none font-medium tracking-tight tabular-nums",
      charactersRemaining < 0 ? "text-red-500" : "",
    )}
    data-testid="sentence-search-character-counter"
    title={
      charactersRemaining >= 0
        ? `${charactersRemaining} characters remaining`
        : `${Math.abs(charactersRemaining)} characters over`
    }
  >
    {counterText}
  </span>
) : null}

// After
suffix={shouldShowCounter ? (
  <span
    className={cn(
      "bg-muted text-muted-foreground inline-flex h-5 items-center rounded-sm px-1.5 text-[9px] font-medium tabular-nums",
      charactersRemaining < 0 ? "bg-red-500/15 text-red-500" : "",
    )}
    data-testid="sentence-search-character-counter"
    title={
      charactersRemaining >= 0
        ? `${charactersRemaining} characters remaining`
        : `${Math.abs(charactersRemaining)} characters over`
    }
  >
    {counterText}
  </span>
) : null}
```

Key changes:
- `bg-muted` → pill background, reads as intentional UI element
- `rounded-sm` → pill shape (mild, consistent with items)
- `px-1.5` → internal padding
- `h-5` → slightly taller for readability
- `text-[9px]` → slightly smaller to not compete with input text
- Over limit: `bg-red-500/15 text-red-500` → red tint pill (not just red text on transparent)

- [ ] **Step 2: Verify badge renders correctly**

Type 35+ chars in search. Counter badge should appear as pill. Type 300+ → red pill.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all pass (counter test checks `data-testid`, not class names).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/chrome/sidebar/sidebar-search-input.tsx
git commit -m "style(search): render char counter as muted badge pill"
```

---

## Self-Review

**Spec coverage:**
- ✅ Corner radius → Task 1 (`rounded-sm` → `rounded-md`)
- ✅ Separator line → Task 2 (soften to `border-border/30`)
- ✅ Character counter → Task 3 (badge with background)

**Placeholder scan:** No TBD, no "implement later", all code shown.

**Type consistency:** No new types introduced.

**Doc impact:** No documentation impact — UI-only changes, no API/schema/command changes.
