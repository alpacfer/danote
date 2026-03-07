# App Controller

Purpose: app-shell composition across domains. This folder coordinates major workflows without owning feature implementation details.

Main entrypoints:
- `use-app-foundation.ts`: shared app-level state and cross-cutting hooks.
- `use-app-controller.ts`: top-level facade consumed by `App.tsx`.
- `use-*-composition.ts`: app-shell composition for playground, wordbank, and developer workflows.

Where to add new behavior:
- Put feature-specific behavior in the domain hooks under `app/hooks/playground/*`, `app/hooks/wordbank/*`, or other feature folders first.
- Only keep cross-feature composition and shell wiring here.
- Put UI prop mapping close to sections under `app/sections/*-section-props.ts`.

Keep these files thin:
- `use-app-controller.ts` should compose domains, not absorb feature logic.
- Generic prop-plumbing helpers should not be reintroduced here unless they encode real shared behavior.
