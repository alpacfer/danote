# `frontend/src/test/app/`

Vitest coverage for user-visible app behavior.

## What Lives Here

- `app-*.test.tsx` files exercise section workflows through rendered UI.
- `mock-fetch.ts` provides backend-shaped API responses and request assertions.
- `wordbank-contract-fixtures.ts` stores reusable wordbank response fixtures.

## What Does Not Live Here

- Production helpers belong in `frontend/src/app/core/` or section folders.
- Component internals should not be tested directly when a user-visible flow can cover them.
- Backend contract changes should also be reflected in backend tests and docs.

## Choosing A File

- Add word detail rendering coverage to `app-wordbank-details.test.tsx`.
- Add word action/request coverage to `app-wordbank-actions.test.tsx`.
- Add sentence flows to `app-sentencebank.test.tsx`.
- Prefer Testing Library queries that match visible text, roles, and outcomes.
