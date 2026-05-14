# danote multi-user roadmap

Three phases. Each one is independently shippable — you can host after Phase 1,
even though it isn't the final shape. Phase 1.5 and Phase 2 are tracked
separately so each can land without the other.

---

## Phase 1 — Hostable shell with accounts and per-user API keys

**Status:** built and reconciled with main's parallel auth work. Ready to
commit and host.

**Goal:** the app is reachable on the public internet, sign-in works, and
each account stores its own encrypted API keys.

**Achieved when:**
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
- Backend's outbound calls (Gemini etc.) still use the host's server-side
  env keys. Saved user keys are stored but not yet consumed. This is
  Phase 1.5.
- All signed-in users share the same wordbank/sentencebank data. This is
  Phase 2.

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

**Status:** not started. This is the smaller of the two remaining phases.

**Goal:** when User A makes a translation request, the backend calls Gemini
with User A's stored key — not the server-wide env key.

**Why this is needed:** today the user-saved keys are inert. The host pays
for all outbound usage. Once this lands, users bring their own billing.

**Achieved when:**
- The four service factories (`gemini_word_translation`, `translation`
  (DeepL + Azure), `tts`, `word_verification`) accept a per-call API key
  rather than binding it at startup.
- Use-case orchestrators (`backend/app/services/use_cases/`) resolve the
  current user's keys via a `RequestContext` and pass them to the factories.
- A new helper module (proposed: `backend/app/core/request_context.py`)
  carries `current_user` plus decrypted keys for the duration of a request.
- The `DANOTE_*_API_KEY` env vars become a fallback (or are removed) so
  that mis-configured users get a clear error rather than silently spending
  the host's quota.
- Tests cover: user A's key is used for user A's calls; missing key returns
  a clear 400/422 rather than 500; decryption errors don't crash the
  request.

**Estimated size:** 1–2 days. The work is localized to the service layer
and use-case orchestration — no DB schema changes.

**Files most likely to touch:**
- `backend/app/services/gemini_translation.py`
- `backend/app/services/translation.py`
- `backend/app/services/tts.py`
- `backend/app/services/sentence_verification.py`
- `backend/app/bootstrap/runtime_*.py` (the factories)
- Use-case modules under `backend/app/services/use_cases/`

**Out of scope:** anything to do with which user *owns* which DB rows.
That's Phase 2.

---

## Phase 2 — Per-user data isolation

**Status:** not started. This is the largest piece.

**Goal:** every user sees only their own wordbank and sentencebank.

**Why this is needed:** today all signed-in users share data. The
multi-tenant promise of "create an account" isn't complete without this.

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
- New tests in `backend/tests/db/test_owner_isolation.py` confirm:
  two users adding the same Danish word get two distinct rows; user A
  cannot read user B's rows through any read endpoint.
- Existing use-case and repo tests are updated to pass an explicit
  `user_id` parameter via the test helpers.
- Read-only reference DBs (`cor.sqlite`, `english_wiki.sqlite`,
  `en_gemini.sqlite`) and the cross-user audio caches stay shared.
- One-time data migration policy: existing rows in a deployed instance
  get assigned to a designated "legacy owner" (`DANOTE_CLAIM_LEGACY_DATA_FOR_USER`)
  on first run after the migration.

**Pitfalls to plan for:**
- `phrase_translations`, `lexemes`, and a few others have `UNIQUE(...)`
  constraints that need to become composite with `owner_user_id`. SQLite
  doesn't drop constraints in place — each needs a table-rebuild pattern
  (create new, copy, drop old, rename, recreate indexes).
- The wordbank FTS index needs to be rebuilt with per-user filtering.
- The background jobs worker (`wordbank_background_jobs`) needs to know
  which user a queued job belongs to.

**Estimated size:** 3–5 days of focused work. Largest risk area: a
half-done isolation pass leaks data across users, which is worse than not
starting. Land it behind a feature flag (`DANOTE_DATA_ISOLATION=1`) so the
migration can be deployed before flipping enforcement on.

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
- Finish threading `owner_user_id` through the rest of the repositories
  and use-cases (the `git status` on main already shows many files in
  progress).
- Add `owner_user_id` to the FTS index used by wordbank search.
- Cover with `backend/tests/db/test_owner_isolation.py` and update
  existing use-case/repo tests.

Then follow `HOSTING.md` for the actual deploy.
