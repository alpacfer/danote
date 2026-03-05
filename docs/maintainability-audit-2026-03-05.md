# Maintainability audit (non-test code)

Date: 2026-03-05 (updated after secondary-candidate notes-editor split)
Scope: application and script code only (test files excluded)

## Method

- Re-ran line counts for non-test `*.ts`, `*.tsx`, `*.py`, `*.md`, `*.sh`, `*.css` files.
- Compared large files against repository guardrails in `AGENTS.md`:
  - target <= 300 lines for production `*.ts`/`*.tsx`
  - hard refactor trigger when a touched file exceeds 450 lines and receives non-trivial changes.

## Progress since initial audit

- ✅ Completed item 1: `frontend/src/app/chrome.tsx` was split into focused modules and a thin barrel.
- ✅ Completed item 2: `frontend/src/App.tsx` was reduced and orchestration moved into dedicated hooks.
- ✅ Completed item 3 (frontend side): `frontend/src/app/chrome/sidebar/app-sidebar.tsx` extracted search and hotkey orchestration into `use-sidebar-search.ts` and `use-sidebar-hotkeys.ts`.
- ✅ Secondary candidate progressed: `frontend/src/components/notes-editor.tsx` moved selection/highlight-click behavior into `notes-editor-selection.ts` and `notes-editor-highlight-click.ts` and dropped from 488 -> 434 lines.
- 🟡 Backend wordbank package split exists, but `backend/app/services/use_cases/wordbank/core.py` remains very large and is still the top maintainability risk.

## Current highest-impact priorities

### 1) `backend/app/services/use_cases/wordbank/core.py` (2184 lines)

**Why it hurts maintainability now**
- The package boundary exists, but most orchestration still lives in a single workflow file.
- Commands, queries, pronunciation IO, verification orchestration, and persistence logic remain co-located.

**Recommended next split**
- `backend/app/services/use_cases/wordbank/commands.py` (mutations: add/update/delete/apply changes)
- `backend/app/services/use_cases/wordbank/queries.py` (list/details/search/read-only paths)
- `backend/app/services/use_cases/wordbank/pronunciation.py` (audio generation + normalization persistence)
- `backend/app/services/use_cases/wordbank/verification.py` (verification workflow + result mapping)
- keep `wordbank/__init__.py` stable as the public import surface

**Outcome expected**
- Lower change blast radius for backend edits and clearer ownership per workflow area.

### 2) `frontend/src/app/chrome/sidebar/app-sidebar.tsx` (766 lines)

**Why it hurts maintainability now**
- Search and hotkeys were extracted, but rendering and ranking composition remain large.
- File still exceeds hard-size threshold for touched TSX files.

**Recommended next split**
- `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` (result sections/groups rendering)
- `frontend/src/app/chrome/sidebar/sidebar-wordbank-results.tsx` (wordbank result row rendering)
- `frontend/src/app/chrome/sidebar/sidebar-cor-results.tsx` (COR grouped variant rendering)
- keep `app-sidebar.tsx` as composition/layout shell

**Outcome expected**
- Smaller UI units, easier targeted tests, and less regression risk in result ordering logic.

### 3) `frontend/src/components/ui/sidebar.tsx` (723 lines)

**Why it hurts maintainability now**
- Many primitives and provider/hook concerns are bundled in one UI module.
- Future feature additions risk cross-cutting changes and churn.

**Recommended next split**
- `frontend/src/components/ui/sidebar-provider.tsx`
- `frontend/src/components/ui/sidebar-rail.tsx`
- `frontend/src/components/ui/sidebar-menu.tsx`
- `frontend/src/components/ui/sidebar-hooks.ts`

**Outcome expected**
- Cleaner primitive ownership and easier incremental UI changes.

## Secondary candidates

- `frontend/src/App.tsx` (440): remains under hard limit; continue composition-only discipline.
- `frontend/src/components/notes-editor.tsx` (434): improved but still above target, so only add logic via helper extraction.
- `frontend/src/app/sections/wordbank-section.tsx` (424): pre-emptive split before crossing 450.
- `backend/app/services/token_classifier.py` (405): extract classifier rule/config tables to reduce branching complexity.
- `backend/app/api/routes/wordbank.py` (371): keep transport-only and avoid orchestration growth.

## Suggested implementation order (updated)

1. Continue backend split of `wordbank/core.py` into workflow modules behind existing package API.
2. Finish sidebar rendering split (`app-sidebar.tsx` -> result-focused presentational modules).
3. Split `components/ui/sidebar.tsx` primitives before further sidebar feature growth.

## Notes

- Recommendations intentionally exclude test files from ranking.
- Prefer behavior-preserving refactors and targeted coverage where behavior moves across module boundaries.
