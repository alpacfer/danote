---
paths:
  - "frontend/src/**/*.ts"
  - "frontend/src/**/*.tsx"
---

# Frontend rules

## Component and hook boundaries

- Components render and handle UI events only — no data fetching, no API calls
- Data fetching and side effects live in hooks (`src/app/hooks/[domain]/`)
- Hooks are organized by domain: `hooks/playground/`, `hooks/wordbank/`, etc.
- `App.tsx` is a thin orchestrator — no workflow logic

## shadcn/ui first

Before building any UI primitive:
1. Check `src/components/ui/` — it may already exist
2. Check shadcn/ui docs for the right component
3. Install via `npx shadcn@latest add <component>` — never handcraft component source
4. Compose around the generated API; style via props/classNames

## TypeScript

- No `any` — use explicit types at all module boundaries
- Keep state shapes typed and named by domain
- Path alias: `@/*` → `./src/*`

## File size limits (enforced by `make maintainability-check`)

| File type | Target | Hard limit |
|---|---|---|
| `.ts` / `.tsx` | ≤ 300 lines | > 450 requires refactor |
| React component | ≤ 200 lines | one main concern |
| Custom hook | ≤ 220 lines | one workflow/domain |
| Function | ≤ 60 lines | split into helpers if deeper |

If you're about to push a file over 450 lines, split it in the same change.
