# Application sections

This directory contains the top-level, navigable application sections and the
small adapters that connect them to app-controller state.

- `wordbank-section.tsx` and `sentencebank-section.tsx` select the list or
  detail composition for their domain.
- `account-section.tsx` owns account-facing rendering and events.
- `developer-section.tsx` is the entrypoint for developer tooling.
- `section-props-adapters.ts` builds explicit section prop bundles.
- Domain-specific rendering belongs in the matching `wordbank/`,
  `sentencebank/`, or `developer/` folder.

Top-level section components should render UI and forward events. Fetching,
workflow orchestration, and cross-section state belong in hooks or services.
Shared primitives belong under `components/ui`; cross-cutting API and display
types belong under `app/core`.

All reachable sections render inside the app shell's canonical `NotebookPage`.
Do not add a competing vertical page scroll area here. Bounded horizontal
scrolling remains appropriate for tables and badge rows.
