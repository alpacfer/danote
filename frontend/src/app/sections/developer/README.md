# Developer section

This directory contains the developer-only tabs and status controls rendered
by the top-level `DeveloperSection`.

- `developer-status-tab.tsx` presents runtime and service health.
- `developer-options-tab.tsx` contains explicit maintenance actions.
- `developer-service-rows.tsx` renders service-specific status rows.
- `developer-word-probe.tsx` handles the focused word probe UI.
- `developer-section-helpers.ts` contains developer-display helpers.

The section owns rendering and UI events only. Runtime fetching, probes, API
key state, and side effects belong in the developer hooks under
`frontend/src/app/hooks/app/`.

Keep destructive maintenance actions explicit and confirmation-backed. Reuse
existing shadcn controls and semantic status types rather than introducing
developer-only primitives. The surrounding `NotebookPage` owns vertical
scrolling and ruling; tabs and popovers use the 8px spacing system without
adding their own notebook background.
