# Versions and Environment Locking

Tracks baseline dev env and dependency locking for reproducibility.

## Environment

- OS: `Linux 6.17.0-14-generic (Ubuntu)`
- Node.js: `v20.20.0`
- Min Node.js for local bootstrap: `20.19.0`
- Package manager: `npm 10.8.2`
- Python: `3.11.x`
- Linux prereqs for backend env: `python3-venv`, `python3-pip`

## Frontend

- Framework: `Vite + React`
- Versions: `Vite 7.3.1`, `React 19.2.0`
- Language: `TypeScript`
- Tailwind: `Tailwind CSS v4 via @tailwindcss/vite plugin`
- shadcn style: `new-york` (default deprecated upstream)
- Aliases: `@/* -> src/*`, `@/components`, `@/lib`, `@/components/ui`
- shadcn config: `frontend/components.json` (used for CLI `add`)
- Font: `Source Sans 3` via `@fontsource/source-sans-3`
- Key libraries:
  - `shadcn 3.8.5`
  - `tailwindcss 4.2.1`
  - `@tailwindcss/vite 4.2.1`
  - `@fontsource/source-sans-3 5.2.9`
  - `radix-ui 1.4.3`
  - `class-variance-authority 0.7.1`
  - `tailwind-merge 3.5.0`
  - `lucide-react 0.575.0`
  - `vitest 4.0.18`
  - `@testing-library/react 16.3.2`

## Backend

- Runtime: `Python 3.11.x`
- Bootstrap target: `run-project.sh` provisions `Python 3.11.x` via `uv`
- Framework: `FastAPI 0.116.1`
- ASGI server: `uvicorn 0.35.0`
- Deps: `pip + pinned requirements files`
- Entrypoint: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- SQLite strategy: `versioned SQL migrations` in `backend/migrations/` with `schema_migrations` tracking
- Schema version: `v0` (`001_init_schema.sql`)
- DB init: `auto-apply migrations on startup`
- Seed loader: `backend/scripts/seed_db.py` (idempotent)
- Seed lexemes: `bog`, `kan`, `lide`
- Lookup service (checkpoint 8): lemma-aware classifier (`known` / `variation` / `new`)
- Analysis endpoint (checkpoint 9): `POST /api/analyze` stable token list schema (see `docs/api-contract.md`)
- NLP adapter: `app/nlp/adapter.py`
- Danish NLP impl: `DaCyLemmyNLPAdapter` in `app/nlp/danish.py`
- Danish NLP model (fixed): `da_dacy_small_trf-0.2.0`
- Key libraries:
  - `fastapi 0.116.1`
  - `uvicorn[standard] 0.35.0`
  - `spacy 3.7.5`
  - `dacy 2.7.8`
  - `lemmy 2.1.0`
  - `pytest 8.4.2` (test)
  - `httpx 0.28.1` (test client transport)
- NLP stack:
  - `spaCy` (core runtime)
  - `DaCy` (Danish pipeline)
  - `Lemmy` (lemmatization)
  - `sqlite3` (stdlib SQLite driver)
- spaCy commands:
  - `python -m spacy download <pipeline_name>`
  - `python -m spacy validate`

## Dependency Locking Policy

- Lockfiles required, must commit.
- Frontend: `package-lock.json` (npm)
- Backend input: `backend/requirements.txt` (+ `backend/requirements-dev.txt` for dev/lock gen)
- Backend canonical lockfile: `backend/requirements.lock.txt`
- First-run bootstrap: `./scripts/run-project.sh` or `uv venv --python 3.11 backend/.venv`

## Current Lockfile Status

- Frontend lockfile: `Yes` (`frontend/package-lock.json`)
- Backend input reqs: `Yes` (`backend/requirements.txt`, `backend/requirements-dev.txt`)
- Backend canonical lockfile: `Yes` (`backend/requirements.lock.txt`)

Update when runtime versions or key deps change.