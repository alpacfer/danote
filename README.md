# danote

Language-learning note-taking web app (Danish-first) with a browser frontend and local Python backend.

## Project Structure

- `frontend/`: web app UI
- `backend/`: Python API, NLP pipeline, and SQLite access
- `docs/`: product definition, API contract, version tracking, test plan
- `scripts/`: development helper scripts
- `test-data/`: seed fixtures and sample sentences

## Documentation Hub

- Start here: [`docs/README.md`](docs/README.md) for the docs map and category index.
- **Hosting**: easiest path is the [Render single-service guide](docs/deployment/render-single-service.md). [`HOSTING.md`](HOSTING.md) and the [VPS private beta guide](docs/deployment/vps-private-beta.md) cover Docker + Caddy.

## Accounts & sign-in

danote requires sign-in (email/password or Google, via Clerk). Each account
manages its own four API keys (Gemini, DeepL, Azure Translation, Azure TTS)
from the **Account** page in the sidebar. The app is gated behind a
"Configure your API keys" screen until all four are saved.

Signed-out users can also choose **Continue as guest**. Guest mode uses the
deployment's host keys, does not require email/password, and creates a fresh
workspace for each guest session. Guest wordbank/sentencebank data is
session-scoped and is not restored when guest mode is started again.

### Free trial

Instead of adding keys, a new user can start a **free trial** from that gate.
The trial runs on the deployment's own host keys and is capped per user per
day (distinct words; repeating a word the same day is free). Configuring all
four keys removes the cap. The trial only works when the backend itself has
host keys configured (`DANOTE_GEMINI_API_KEY` plus translation/TTS keys);
otherwise the gate reports the trial as unavailable.

| Env var | Default | Purpose |
|---|---|---|
| `DANOTE_TRIAL_ENABLED` | `1` | Master switch for the free trial. |
| `DANOTE_TRIAL_DAILY_SEARCH_LIMIT` | `50` | Distinct word searches allowed per user per day. |
| `DANOTE_GUEST_DAILY_SEARCH_LIMIT` | `20` | Distinct word searches allowed per guest browser per day. |
| `DANOTE_TRIAL_RESET_TIMEZONE` | `Europe/Copenhagen` | Timezone whose local midnight resets the daily counter. |

For local development without auth, set `DANOTE_AUTH_ENABLED=0` in your
`.env` to bypass the gate and use a fixed dev user. With auth disabled the
trial is not metered.

## Run Instructions

## Developer Quickstart

```bash
cd <repo-root>
make setup
make lint
make maintainability-check
make test
```

For ongoing documentation/workflow verification:

```bash
cd <repo-root>
make docs-smoke
```

For live API debugging and terminal-level feature verification:

```bash
cd <repo-root>
scripts/dev-app.py health
scripts/dev-app.py wordbank details <lemma>
scripts/dev-app.py wordbank category-status <lemma> --polls 5 --expect-category Food
scripts/dev-app.py search profile <query>
scripts/dev-app.py search trace <english-query>
scripts/dev-app.py search all <query>
```

`scripts/dev-app.py` is the **Danote Terminal Controller** (**DTC**). It
auto-detects the local backend, calls the same API routes as the frontend, and
emits JSON only. After implementing a feature that is reachable through the app
API, run at least one relevant DTC command as an extra acceptance check
alongside the normal targeted test set. The older `scripts/dev-search-debug.py`
remains available for human-readable search traces.
`search profile` splits backend processing from client overhead when the live
backend exposes its timing header. Cold-cache profiling with `--cold-cache`
requires `DANOTE_SEARCH_ADMIN_ENABLED=1` on the backend.

Backend pytest sessions automatically restore the tracked Gemini audit log
`backend/data/gemini-applied-changes.jsonl` at session end so test runs do not
leave that file dirty.

For day-to-day changes, do not default to the full suite every time. Run the
smallest relevant verification set first:

- docs/workflow-only changes: `make docs-smoke`
- frontend-only changes: run the nearest affected Vitest file(s)
- backend-only changes: run the nearest affected pytest module(s)

Reserve `make lint`, `make test`, and `make docs-smoke` together for broad or
high-risk work such as cross-cutting changes, multi-module refactors,
dependency/build/config updates, or anything whose blast radius is unclear.

For AI-agent full verification on broad changes:

```bash
cd <repo-root>
make agent-verify
```

Agent guidance:

- `AGENTS.md` is the source of truth.
- `CLAUDE.md` is a compatibility symlink for Claude Code.
- `.codex/config.toml` keeps project-scoped sandbox/approval defaults; Codex finds `AGENTS.md` natively.

One-command startup (recommended):

```bash
cd <repo-root>
./scripts/run-project.sh
```

This starts backend and frontend together, checks backend health, and stops only the processes it started on `Ctrl+C`.
Defaults are stable: backend `http://127.0.0.1:8000`, frontend `http://127.0.0.1:5173`.
If a healthy backend or frontend is already running on those ports, the script reuses it.
If a port is occupied by something unhealthy, startup fails with a clear message instead of silently opening another port.
It also auto-loads root-level `.env` and `.env.local` files when present.
Those files use dotenv syntax, not shell syntax: one `KEY=value` assignment
per line, optional quotes around values, blank lines and `#` comments allowed.
Replace angle-bracket placeholders before startup.
On macOS and Linux, the script now self-heals the backend bootstrap path: it installs `uv`
user-locally when missing, provisions Python `3.11`, recreates stale backend virtualenvs, and installs
`backend/requirements.lock.txt`. The previous DaCy/spaCy/Lemmy stack and
`da_dacy_small_trf-0.2.0` model are retired for now and are not installed or loaded by default.
`node` and `npm` are still required locally; when they are missing or too old, the script prints
platform-specific install commands and exits before partial startup.

Configuration reference: [`docs/reference/configuration-reference.md`](docs/reference/configuration-reference.md).
Easiest hosted deployment guide: [`docs/deployment/render-single-service.md`](docs/deployment/render-single-service.md).
VPS private beta deployment guide: [`docs/deployment/vps-private-beta.md`](docs/deployment/vps-private-beta.md).
Hosted Render + Vercel deployment runbook: [`docs/deployment/render-vercel.md`](docs/deployment/render-vercel.md).
VPS preflight: `make hosting-check` validates the current env file and Docker
Compose config without printing secrets.

### Configuration precedence

For backend settings, value resolution is:

1. exported environment variables
2. `<repo-root>/.env.local`
3. hardcoded defaults

Example (`.env.local`):

```bash
DANOTE_TTS_AZURE_API_KEY=your-speech-key
DANOTE_TTS_AZURE_REGION=your-speech-region
DANOTE_WORD_VERIFICATION_GEMINI_API_KEY=your-gemini-key
DANOTE_WORDBANK_BACKGROUND_JOB_WORKERS=4
DANOTE_SEARCH_GEMINI_CACHE=1
DANOTE_SEARCH_PARALLEL=1
DANOTE_SEARCH_WARMUP=1
```

See the full per-variable reference (defaults, accepted values, and fallback interactions) in [`docs/reference/configuration-reference.md`](docs/reference/configuration-reference.md).

Word verification, pronunciation, and related-word enrichment now run through the shared wordbank queue.
`DANOTE_WORDBANK_BACKGROUND_JOB_WORKERS` controls how many queued wordbank jobs can execute in parallel.
Automatic wordbank add/save/complete flows enqueue pronunciation work through that shared queue and return `queued_pronunciation_forms` so the frontend can poll until audio is persisted.
Sentencebank saves now enqueue sentence-level pronunciation through that same shared queue; saved sentence payloads expose `has_pronunciation`, and the sentence page header supports click-to-listen plus right-click regeneration.
Automatic wordbank add/save flows also enqueue lemma-scoped related-word resolution for compound decomposition, and the saved word page snapshot now exposes `related_words.status` so the frontend can poll silently until related cards are ready.
Related-word verb translations are normalized to English infinitive form (`to <verb>`), and compound links are bidirectional on saved word pages: saving `legeplads` will also surface `legeplads` as related on the saved `lege` and `plads` pages.
When related-word enrichment points at an already-saved target and Gemini returns a different valid translation, that translation is persisted as an additional translation on the saved target word page instead of being discarded or waiting for a manual add.
Word verification may use COR glosses and translated glosses as internal sense clues for homographs, but Gemini review output is limited to lemma/meaning translation feedback and must not propose or describe gloss changes.

NLP status:

- `DANOTE_NLP_ENABLED` defaults to `0`.
- `/api/analyze` is unavailable unless a future NLP adapter is added and enabled.
- Playground is retired/inaccessible in the frontend while the NLP stack is disabled.

Local workflow:

1. Start backend service.
2. Start frontend dev server.
3. Open the app in a browser and connect to local backend.

Backend:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `python3-venv` / `python3-pip` are missing on Linux, bootstrap with `uv` first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv python install 3.11
~/.local/bin/uv venv --clear backend/.venv
~/.local/bin/uv pip install --python backend/.venv/bin/python -r backend/requirements.lock.txt
```

Frontend runtime floor:

- Node.js `>=20.19.0`
- npm available on `PATH`

Frontend:

```bash
cd frontend
npm install
# optional if backend is not on default http://127.0.0.1:8000
# export VITE_BACKEND_URL=http://127.0.0.1:8000
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Connectivity check:

- Frontend calls `GET /api/health` on startup.
- Backend returns readiness payload with `status: ok|degraded`.

Database init and seed:

- Backend startup auto-creates/migrates SQLite schema.
- Source-controlled DB asset: `backend/resources/dictionaries/cor.sqlite` (canonical dictionary source).
- Source-controlled English source data: `backend/resources/dictionaries/english_wiki.jsonl`.
- Built English dictionary asset: `backend/resources/dictionaries/english_wiki.sqlite` (used for English sidebar lookup/translation fallback).
- Runtime-generated SQLite artifacts (`*.sqlite-shm`, `*.sqlite-wal`, `*.sqlite3-shm`, `*.sqlite3-wal`) are local-only and ignored by Git.
- Run idempotent seed loader:

```bash
cd backend
./.venv/bin/python scripts/seed_db.py
```

Build/update the local English dictionary SQLite:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/build_english_sqlite.py \
  --input resources/dictionaries/english_wiki.jsonl \
  --output resources/dictionaries/english_wiki.sqlite
```

Queue repair for existing wordbank pronunciation gaps:

```bash
cd <repo-root>
PYTHONPATH=backend backend/.venv/bin/python scripts/queue-missing-pronunciations.py --dry-run
PYTHONPATH=backend backend/.venv/bin/python scripts/queue-missing-pronunciations.py
```

## Regression Baseline (Checkpoint 18)

Fixture pack:

- Notes and seed fixtures: `test-data/fixtures/`
- Golden analyze fixture generation and regression tests are retired while DaCy NLP is disabled.

Run scripted e2e reliability flow:

```bash
cd <repo-root>
./scripts/e2e-regression.sh
```

Behavior and workflow docs:

- `docs/behavior/app-shell-behavior.md`
- `docs/behavior/sentencebank-section-behavior.md`
- `docs/behavior/sidebar-search-behavior.md`
- `docs/behavior/wordbank-section-behavior.md`
- `docs/behavior/playground-section-behavior.md`
- `docs/behavior/notes-section-behavior.md`
- `docs/behavior/developer-section-behavior.md`
- `docs/testing/test-plan.md`

## Reproducibility

- Lockfiles must be committed when dependencies are introduced.
- Environment/runtime versions are tracked in `docs/reference/versions.md`.


## Priority C references

- Backend dependency locking: `docs/architecture/backend-dependency-locking.md`
- ADR index: `docs/architecture/adr/README.md`
- Test pyramid + CI split: `docs/testing/test-pyramid-and-ci.md`
