# Maintainability audit (non-test code)

Date: 2026-03-05
Scope: application and script code only (test files excluded)

## Method

- Measured line counts for non-test `*.ts`, `*.tsx`, `*.py`, `*.md`, `*.sh`, `*.css` files.
- Compared large files against repository guardrails in `AGENTS.md`:
  - target <= 300 lines for production `*.ts`/`*.tsx`
  - hard refactor trigger when a touched file exceeds 450 lines and receives non-trivial changes.

## Highest-impact candidates

### 1) `frontend/src/app/chrome.tsx` (1097 lines)

**Why it hurts maintainability**
- Mixes reusable UI components (`ThemeToggleButton`, `AppBreadcrumb`) with a very large `AppSidebar` orchestration surface.
- Sidebar command/search behavior, async query logic, caching, and rendering all coexist in one file.

**Recommended split**
- `frontend/src/app/chrome/app-breadcrumb.tsx`
- `frontend/src/app/chrome/theme-toggle-button.tsx`
- `frontend/src/app/chrome/sidebar/app-sidebar.tsx` (render-only composition)
- `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` (fetch/debounce/cache + derived matches)
- `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` (result list rendering)

**Outcome expected**
- Smaller review units, easier ownership boundaries, and lower regression risk around search behavior.

### 2) `frontend/src/App.tsx` (635 lines)

**Why it hurts maintainability**
- Root composition file also owns many domain-specific state variables and orchestration concerns.
- Includes developer settings, note workspace control flow, wordbank workflows, and section routing in one component.

**Recommended split**
- `frontend/src/app/providers/app-state-provider.tsx` for shared app-level state.
- `frontend/src/app/hooks/use-developer-settings.ts` for API key/model/reset behavior.
- `frontend/src/app/hooks/use-section-navigation.ts` for section/selection transitions.
- Keep `App.tsx` as thin shell that composes providers + layout.

**Outcome expected**
- `App.tsx` becomes a high-level composition file (closer to guardrail intent) and easier to reason about.

### 3) `backend/app/services/use_cases/wordbank.py` (2399 lines)

**Why it hurts maintainability**
- Central use-case file likely aggregates too many workflows (lookup, add/update/delete, pronunciation, verification, search helpers).
- Hard to navigate and difficult to run focused edits without incidental coupling.

**Recommended split (by workflow)**
- `backend/app/services/use_cases/wordbank/commands.py` (mutations)
- `backend/app/services/use_cases/wordbank/queries.py` (read/list/search)
- `backend/app/services/use_cases/wordbank/pronunciation.py`
- `backend/app/services/use_cases/wordbank/verification.py`
- `backend/app/services/use_cases/wordbank/mappers.py` (DTO/domain mapping helpers)
- keep `__init__.py` as stable public surface

**Outcome expected**
- More discoverable domain boundaries and lower cognitive load for backend changes.

## Secondary candidates

- `frontend/src/components/ui/sidebar.tsx` (723): shared UI primitive can be split into structural pieces (`provider`, `rail`, `menu`, `hooks`) if further feature work is needed.
- `frontend/src/components/notes-editor.tsx` (488): close to hard trigger; extract keyboard shortcut handling and selection helpers.
- `frontend/src/app/sections/wordbank-section.tsx` (424): pre-emptive split into presentational subcomponents before it crosses 450.
- `backend/app/services/token_classifier.py` (405): extract classifier rules/config tables into dedicated modules to reduce branching density.
- `backend/app/api/routes/wordbank.py` (371): route file is still acceptable, but it should remain thin as use-case module split progresses.

## Suggested implementation order

1. Frontend low-risk split: `chrome.tsx` into focused modules with no behavior changes.
2. Frontend app-shell split: reduce `App.tsx` to composition + provider wiring.
3. Backend major split: carve `wordbank.py` into workflow modules behind same public API.

## Notes

- These recommendations intentionally exclude test files from ranking, as requested.
- Prioritize behavior-preserving refactors plus snapshot/interaction coverage for the split areas.
