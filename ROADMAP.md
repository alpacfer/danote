# danote multi-user roadmap

Three phases. Each one is independently shippable — you can host after Phase 1,
even though it isn't the final shape. Phase 1.5 has shipped, and Phase 2 is
partially implemented but still needs broader isolation verification before a
public multi-user rollout.

---

## Phase 1 — Hostable shell with accounts and per-user API keys

**Status:** built and reconciled with main's parallel auth work. Ready to
commit and host.

**Goal:** the app is reachable on the public internet, sign-in works, and
each account stores its own encrypted API keys.

**Done when:**
- Visiting `https://your-domain` shows a sign-in screen for signed-out users
  (Google + email/password, both via Clerk).
- A signed-in user with zero keys configured sees the **Configure your API
  keys** screen and is blocked from the rest of the app.
- After saving all four keys (Gemini, DeepL, Azure Translation, Azure TTS)
  the main app loads.
- The **Account** page in the sidebar (`Alt + A`) shows masked keys with
  Set / Not set badges, lets the user replace or remove a key, and exposes
  Clerk's `UserButton` for profile/password.
- The Docker image builds and `docker compose up -d` brings the app online
  behind Caddy with auto-TLS.
- `HOSTING.md` is the canonical recipe.

**Out of scope for Phase 1 (handled later):**
- Backend outbound calls using the calling user's stored API keys. This
  shipped in Phase 1.5.
- Complete confidence in per-user wordbank/sentencebank isolation. Phase 2
  is partially implemented and still needs broader isolation verification.

**How this was reconciled with main's parallel work:**
- Clerk SDK: kept main's `@clerk/react@^6.6.2`; removed `@clerk/clerk-react`.
- Sign-in UI: kept main's `AuthenticatedApp` in `frontend/src/App.tsx`.
  The new `ApiKeysGate` is wedged between the "signed in" check and
  `<AppShell />`, so the key-setup screen only appears after Clerk says the
  user is authenticated.
- Auth header injection: kept main's `getAuthToken()` pattern in
  `frontend/src/app/core/auth-token.ts` + `api-client.ts`; deleted my
  duplicate `setAuthTokenProvider`/`resolveAuthHeaders` block.
- `/api/me` (main's) and `/api/account/me` (new) coexist — they return
  slightly different shapes for different consumers.
- Migration numbering: main's `027_user_isolation.sql` creates `app_users`
  and starts the data-isolation pass (Phase 2). The new
  `028_user_api_keys.sql` only adds the `user_api_keys` table.
- Local-dev seed user: aligned with main's `('local', 'local-dev',
  'local@danote.local')` row from migration 027.

**Before committing:**
1. `cd frontend && npm install` (already done — `@clerk/react` is installed).
2. `make lint && make test` and address any failures.
3. Manual smoke: `docker compose up --build`, sign up, configure 4 keys,
   confirm the gate flips and the main app loads.

---

## Phase 1.5 — Outbound calls use the calling user's API keys

**Status:** shipped.

**Goal:** when User A makes a translation request, the backend calls Gemini
with User A's stored key — not the server-wide env key.

**Why this is needed:** saved user keys must affect outbound calls so hosted
instances can support bring-your-own-provider billing instead of always using
host-level keys.

**Achieved when:**
- User API keys are stored encrypted in `user_api_keys`.
- `UserServiceResolver` builds a per-request `BackendServices` bundle from
  the calling user's stored keys.
- Wordbank, sentencebank, and background job paths resolve services for the
  current user before making Gemini / DeepL / Azure calls.
- Host-level `DANOTE_*_API_KEY` values remain optional fallbacks when a user
  has not configured a given provider.
- Targeted tests cover user-key service swapping and fallback behavior.

**Out of scope:** anything to do with which user *owns* which DB rows.
That's Phase 2.

---

## Phase 2 — Per-user data isolation

**Status:** partially implemented; needs broader owner-isolation verification before public multi-user hosting.

**Goal:** every user sees only their own wordbank and sentencebank.

**Why this is needed:** the app should guarantee that each signed-in user sees
only their own saved wordbank and sentencebank data.

**Achieved when:**
- Every user-owned data table has `owner_user_id INTEGER NOT NULL`:
  - lexemes, lexeme_meanings, surface_forms
  - phrase_translations
  - sentence_bank, sentence_bank_tokens, sentence_bank_tokens_next
  - wordbank_background_jobs, wordbank_verification_records
  - wordbank_categories, wordbank_category_assignments
  - wordbank_related_words, wordbank_additional_translations
  - ignored_tokens, typo_feedback
  - verification_change_log, token_events
- Every repository read filters by `WHERE owner_user_id = :user_id`.
- Every insert sets `owner_user_id`.
- Every update/delete adds `AND owner_user_id = :user_id` to the WHERE.
- Use-case orchestrators (`backend/app/services/use_cases/`) thread
  `current_user.id` from the route into the repos.
- Owner-isolation tests confirm that two users adding the same Danish word get
  distinct rows and that user A cannot read user B's rows through persisted
  read endpoints.
- Existing use-case and repo tests are updated to pass an explicit
  `user_id` parameter via the test helpers.
- Read-only reference DBs (`cor.sqlite`, `english_wiki.sqlite`,
  `en_gemini.sqlite`) and the cross-user audio caches stay shared.
- Existing rows in a deployed instance have a documented migration/ownership
  policy before public multi-user access is enabled.

**Pitfalls to plan for:**
- `phrase_translations`, `lexemes`, and a few others have `UNIQUE(...)`
  constraints that need to become composite with `owner_user_id`. SQLite
  doesn't drop constraints in place — each needs a table-rebuild pattern
  (create new, copy, drop old, rename, recreate indexes).
- The wordbank FTS index needs to be rebuilt with per-user filtering.
- The background jobs worker (`wordbank_background_jobs`) needs to know
  which user a queued job belongs to.

**Estimated size:** 3–5 days of focused verification and cleanup. Largest
risk area: a half-done isolation pass leaks data across users, which is worse
than not starting. Keep hosted rollout private until owner-isolation checks
cover the persisted routes.

**What's already on main (started in `027_user_isolation.sql`):**
- `app_users` table.
- `owner_user_id` added with composite-unique rebuild on: `lexemes`,
  `phrase_translations`, `sentence_bank`, `ignored_tokens`,
  `wordbank_background_jobs`.
- `owner_user_id` column added (no rebuild) on: `token_events`,
  `typo_feedback`, `verification_change_log`.
- Repository read/write paths under `backend/app/db/repositories/` partially
  updated to thread `owner_user_id` through queries.
- Use-case orchestrators in `backend/app/services/use_cases/` partially
  updated to consume `current_user.id`.

**Remaining for Phase 2:**
- Audit every persisted read/write route and repository for owner scoping,
  including less-traveled verification, category, typo, and token-event paths.
- Broaden tests from the current targeted repository coverage to
  cross-endpoint owner-isolation scenarios.
- Run a Docker smoke with two users before treating the deployment as public
  multi-user ready.

Then follow `HOSTING.md` for the actual deploy.
