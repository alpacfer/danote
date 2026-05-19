# `frontend/src/app/auth/`

Sign-in adjacent UI and the API-key / free-trial gate that sits between a
signed-in user and the app shell. Clerk provider wiring lives in
`frontend/src/main.tsx`; this folder is the danote-side account surface.

## File map

| File | Role |
|---|---|
| `account-api.ts` | Typed client + types for `/api/account/*` (status, keys, trial opt-in) and the account error-message map. |
| `use-account-status.ts` | Hook that fetches/refetches `AccountStatus` (keys + trial). |
| `api-keys-gate.tsx` | Gate: renders children only when keys are configured **or** the free trial is opted into; otherwise shows the setup screen. |
| `api-key-setup-screen.tsx` | Pre-entry screen: the keys form plus the "Start free trial" CTA. |
| `api-keys-form.tsx` | The four-provider key entry/save/delete form (reused on the Account page). |
| `guest-entry-screen.tsx` | Signed-out guest CTA UI. |
| `guest-session.ts` | Browser-id/session-token storage and `POST /api/guest/sessions` client. |
| `guest-account-cards.tsx` | Guest profile and usage cards for the Account section. |

## Rules

- The gate is transparent when `enabled` is false (local dev, auth disabled).
- Trial state is server-authoritative — read it from `AccountStatus.trial`;
  do not infer trial eligibility client-side.
- Keep network/types in `account-api.ts`; components stay presentational.
