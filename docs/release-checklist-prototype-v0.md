# Release Checklist - Prototype v0

## Build and Install

- [ ] Clean install works (`npm ci` in `frontend`, venv install in `backend`).
- [ ] Lockfiles are committed and unchanged after clean install.

## Data and Startup

- [ ] SQLite DB initializes automatically on backend startup.
- [ ] Seed command runs successfully: `backend/scripts/seed_db.py`.
- [ ] Backend starts and exposes `/api/health`.
- [ ] Frontend starts and can connect to backend.

## Core UX

- [ ] Header health badge reflects backend state.
- [ ] Canonical example passes: `Jeg kan godt lide bogen`.
- [ ] Add-word flow passes for unknown token (`kat`).
- [ ] Duplicate add is graceful (no crash, friendly message).

## Reliability

- [ ] Backend restart preserves wordbank entries.
- [ ] Frontend restart reconnects and remains usable.
- [ ] Invalid DB path is surfaced as degraded backend state.
- [ ] NLP startup failure is surfaced as degraded backend state.

## Regression and Tests

- [ ] Backend full suite passes.
- [ ] Frontend full suite passes.
- [ ] Fixture regression test suite passes.
- [ ] E2E regression script passes.
- [ ] Manual demo script executed once end-to-end.

## Tag Readiness

- [ ] `docs/versions.md` updated if dependencies changed.
- [ ] `docs/api-contract.md` reflects current endpoints.
- [ ] `docs/manual-demo-script.md` reviewed and accurate.
- [ ] Release notes prepared for prototype tag.
