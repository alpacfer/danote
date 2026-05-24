# `frontend/src/app/chrome/sidebar/`

Sidebar chrome for global navigation and command search. Keep files here focused on the app shell sidebar, not section-specific page UI.

## File map

| File | Role |
|---|---|
| `app-sidebar.tsx` | Composes the sidebar shell, command dialog, navigation, and footer actions. |
| `app-sidebar-types.ts` | Public prop contract for the sidebar shell. |
| `mobile-bottom-nav.tsx` | Floating bottom pill navigation bar for mobile devices. |
| `sidebar-navigation.tsx` | Static navigation actions and keyboard shortcut labels. |
| `sidebar-search-input.tsx`, `sidebar-search-results.tsx` | Command search input and result rendering. |
| `sidebar-search-skeletons.tsx` | Loading placeholders shared by search result flows. |
| `sidebar-*-results.tsx`, `sidebar-sentence-result.tsx` | Result presenters for each search source. |
| `sidebar-page-items.ts` | Searchable app page definitions and navigation actions. |
| `sidebar-search-query.ts` | Shared query normalization and mode detection. |
| `use-sidebar-*.ts` | Sidebar-only hooks for hotkeys, search orchestration, ranking, selection, and search-dialog history. |

## Rules

- Keep route or section orchestration out of this directory; pass actions in through `AppSidebarProps`.
- Use shadcn sidebar primitives from `@/components/ui/sidebar` for layout and menu controls.
- Add shared, cross-section types to `frontend/src/app/core/` instead of defining them here.
- Prefer source-specific result components over expanding `sidebar-search-results.tsx` with new branches.
