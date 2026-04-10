# Developer Page Restructure — Design Spec

**Date:** 2026-04-10
**Status:** Approved

## Problem

The current developer page is a single flat card with all concerns (backend status, API status, NLP model, API keys, probe tests, database reset) crammed into one vertical list. It's visually cluttered, hard to scan, and the frequently-used "Delete DB" button is buried at the bottom.

## Design Decisions

### Layout: shadcn Tabs

Replace the single card with a `Tabs` component (shadcn/ui) containing 4 tabs:

| Tab | Content |
|---|---|
| **Status** | Backend connection badge + URL, 2x2 service status grid, NLP model selector |
| **API Keys** | Translation provider selector, key fields grouped by service (Translation, TTS, Gemini), Apply button |
| **Probes** | Test buttons + inline results, grouped by service |
| **Database** | Full delete DB + clear cache action with confirmation, explanation of what gets cleared |

### Sticky Action Bar

A sticky bottom bar visible from any tab containing:
- "Danger zone" label on the left
- "Delete DB + Clear cache" destructive button on the right
- Brief description text

### Cache Clearing Behavior

When the user presses "Delete DB + Clear cache":

1. Show confirmation dialog ("This will delete the database and clear all browser cache. Continue?")
2. Delete the backend database via `DELETE /api/wordbank/database`
3. Clear `localStorage` (all keys)
4. Clear `sessionStorage` (all keys)
5. Unregister all service workers
6. Clear all Cache API entries (`caches.keys()` → `caches.delete()`)
7. Run existing `runAppDatabaseResetWorkflow` to reset in-memory app state
8. Force a hard page reload via `window.location.reload()`

Steps 2-7 run sequentially. If step 2 (DB deletion) fails, show error toast and stop — don't clear cache. Steps 3-7 are cleanup and should proceed if the DB deletion succeeds.

## File Changes

### New files

- `frontend/src/app/sections/developer/developer-section.tsx` — main section with Tabs + sticky bar
- `frontend/src/app/sections/developer/status-tab.tsx` — Status tab content
- `frontend/src/app/sections/developer/api-keys-tab.tsx` — API Keys tab content
- `frontend/src/app/sections/developer/probes-tab.tsx` — Probes tab content
- `frontend/src/app/sections/developer/probe-result.tsx` — reusable probe result display (moved from root)
- `frontend/src/app/sections/developer/database-tab.tsx` — Database tab content
- `frontend/src/app/sections/developer/index.ts` — barrel export

### Modified files

- `frontend/src/app/sections/developer-section-props.ts` — add cache clearing callback prop
- `frontend/src/app/hooks/app/use-developer-settings.ts` — add cache clearing logic to `resetDatabase`
- `frontend/src/app/hooks/app/controller/use-developer-composition.ts` — no changes expected (cache clearing happens inside the hook)

### Deleted files

- `frontend/src/app/sections/developer-section.tsx` — replaced by `developer/` directory
- `frontend/src/app/sections/developer-probe-result.tsx` — moved to `developer/probe-result.tsx`

### No backend changes

The backend already supports `DELETE /api/wordbank/database`. No new endpoints needed.

## shadcn Components Used

- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` — tab navigation (check if already installed)
- `Card`, `CardContent`, `CardHeader`, `CardTitle` — already in use
- `Badge` — already in use
- `Button` — already in use
- `Input` — already in use
- `Label` — already in use
- `Select` — already in use

## Component Structure

```
DeveloperSection (tabs shell + sticky bar)
├── StatusTab
│   ├── Connection card (badge + URL)
│   ├── Service status grid (2x2 badges)
│   └── NLP model selector
├── ApiKeysTab
│   ├── Translation provider selector
│   ├── Translation key fields (DeepL or Azure)
│   ├── TTS key fields (Azure)
│   ├── Gemini key field
│   └── Apply button
├── ProbesTab
│   ├── Translation probe (button + result)
│   ├── Speech probe (button + result)
│   └── Gemini probe (button + result)
└── DatabaseTab
    └── Delete action with explanation
```

Each tab component receives only the props it needs — no prop drilling through the parent.

## Verification

- Frontend: `cd frontend && npx vitest run` for affected test files
- Maintainability: `make maintainability-check` to verify file sizes
- Lint: `make lint`
- No backend changes, so no backend tests needed
