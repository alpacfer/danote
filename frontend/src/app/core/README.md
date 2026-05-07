# `frontend/src/app/core/`

Cross-cutting frontend primitives used by sections, hooks, and chrome. Flat layout.

## File map

| File | Role |
|---|---|
| `api-client.ts`, `api-runtime.ts` | Fetch wrappers + runtime API helpers used by hooks. |
| `types-api.ts`, `types-app-api.ts`, `types-runtime-api.ts`, `types-wordbank-api.ts`, `types-wordbank-details-api.ts`, `types-sentencebank.ts`, `types-ui.ts` | TypeScript types mirroring backend DTOs and shared UI shapes. Keep these in sync with `backend/app/api/schemas/v1/`. |
| `storage.ts` | Local storage / persistence helpers. |
| `constants.ts` | Shared constants. Add here only if used in 2+ places. |
| `morphology.ts`, `cor.ts`, `text-utils.ts` | Danish-language utilities (token shape, COR helpers, text trimming). |
| `semantic-categories.ts` | Static semantic category metadata. |
| `audio-verification.ts`, `word-verification.ts` | Verification-state helpers used by hooks. |
| `app-reset-workflow.ts` | Cross-cutting reset flow. |
| `index.ts` | Barrel re-exports for the most common entry points. |

## Rules

- Pure logic and shared types only — no React components, no DOM access.
- If a helper is used in only one section, move it next to that section instead.
- Keep type files (`types-*.ts`) the canonical source for API shapes; do not redefine in components.
