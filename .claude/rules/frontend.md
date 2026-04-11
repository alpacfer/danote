---
paths:
  - "frontend/src/**/*.ts"
  - "frontend/src/**/*.tsx"
---

# Frontend rules

## Component and hook boundaries

- Components: render + UI events only. No fetch, no API calls.
- Fetch + side effects → hooks (`src/app/hooks/[domain]/`)
- Hooks by domain: `hooks/playground/`, `hooks/wordbank/`, etc.
- `App.tsx` thin orchestrator. No workflow logic.

## shadcn/ui first

Before any UI primitive:
1. Check `src/components/ui/` — may already exist
2. Check shadcn/ui docs for right component
3. Install via `npx shadcn@latest add <component>` — never handcraft source
4. Compose on generated API. Style via props/classNames.

## TypeScript

- No `any`. Explicit types at module boundaries.
- State: typed, domain-named.
- Path alias: `@/*` → `./src/*`

## File size limits (enforced by `make maintainability-check`)

| File type | Target | Hard limit |
|---|---|---|
| `.ts` / `.tsx` | ≤ 300 lines | > 450 requires refactor |
| React component | ≤ 200 lines | one main concern |
| Custom hook | ≤ 220 lines | one workflow/domain |
| Function | ≤ 60 lines | split into helpers if deeper |

File >450 lines: split in same change.