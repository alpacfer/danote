# `frontend/src/app/hooks/`

Application hooks that coordinate data loading, workflows, and app-level state.

## What Lives Here

- `use-lexicon-data.ts` owns wordbank/sentencebank loading and refresh polling.
- `use-wordbank-workflows.ts` wires user actions to API calls and section state updates.
- `use-analysis.ts`, note hooks, and notification hooks keep adjacent app workflows separate.
- Domain subfolders (`wordbank/`, `sentencebank/`, `playground/`, `app/`) hold smaller workflow hooks.

## What Does Not Live Here

- Rendering belongs in `frontend/src/app/sections/` or chrome components.
- Shared pure types and helpers belong in `frontend/src/app/core/`.
- UI primitives belong in `frontend/src/components/ui/`.

## Choosing A File

- Add API orchestration to the smallest domain hook that owns the workflow.
- Add cross-section refresh/loading state to `use-lexicon-data.ts`.
- Keep side effects out of components; expose handlers and derived state from hooks.
- When a hook grows, extract a domain hook under the matching subfolder.
