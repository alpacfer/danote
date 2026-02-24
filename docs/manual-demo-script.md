# Manual Demo Script (Prototype v0)

## Goal

Demonstrate the core loop: note analysis, add-to-wordbank, and persistence across restart.

## Preconditions

- Repository cloned cleanly.
- Backend environment installed (`backend/.venv`).
- Frontend dependencies installed (`frontend/node_modules`).
- Backend and frontend start script available: `./scripts/run-project.sh`.

## Demo Steps

1. Start the full stack:
   - `cd /home/alejandro/Documents/github/danote/danote`
   - `./scripts/run-project.sh`
2. Open browser at `http://127.0.0.1:4173`.
3. Verify health badge in header:
   - Expected: `connected` (or `degraded` if backend reports degraded mode).
4. In `Notes`, type:
   - `Jeg kan godt lide bogen `
5. Open `Detected words` tab and verify:
   - `kan` is `known`
   - `bogen` is `variation`
6. Type unknown word in `Notes`:
   - `kat `
7. Open `Detected words` and click `Add` on `kat` row.
8. Verify success toast appears.
9. Wait for auto-refresh/re-analysis:
   - Expected: `kat` now appears as `known`.
10. Stop both services with `Ctrl+C`.
11. Restart stack:
    - `./scripts/run-project.sh`
12. Re-enter `kat ` in `Notes`.
13. Confirm persistence:
    - Expected: `kat` still classified as `known` after restart.

## Fallback Checks

- If health badge is `offline`, confirm backend is running on `127.0.0.1:8000`.
- If badge is `degraded`, check backend logs for `db_error` / `nlp_error` details.
