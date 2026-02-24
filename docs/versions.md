# Versions and Environment Locking

This document tracks the baseline development environment and dependency locking choices for reproducibility.

## Environment

- OS: `Linux 6.17.0-14-generic (Ubuntu)`
- Node.js: `v20.20.0`
- Package manager: `npm 10.8.2`
- Python: `3.12.3`
- Linux prerequisites for backend env setup: `python3-venv`, `python3-pip`

## Frontend

- Framework: `Vite + React`
- Framework version: `Vite 7.3.1`, `React 19.2.0`
- Language mode: `TypeScript`
- Tailwind setup: `Tailwind CSS v4 via @tailwindcss/vite plugin`
- shadcn style: `new-york` (default style is deprecated upstream)
- Alias conventions: `@/* -> src/*`, `@/components`, `@/lib`, `@/components/ui`
- shadcn config file: `frontend/components.json` (present and used for CLI `add`)
- Key libraries:
  - `shadcn 3.8.5`
  - `tailwindcss 4.2.1`
  - `@tailwindcss/vite 4.2.1`
  - `radix-ui 1.4.3`
  - `class-variance-authority 0.7.1`
  - `tailwind-merge 3.5.0`
  - `lucide-react 0.575.0`
  - `vitest 4.0.18`
  - `@testing-library/react 16.3.2`

## Backend

- Runtime: `Python 3.12.3`
- Framework: `FastAPI 0.116.1`
- ASGI server: `uvicorn 0.35.0`
- Dependency management approach: `pip + pinned requirements files`
- Backend entrypoint: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- SQLite schema strategy: `versioned SQL migrations` in `backend/migrations/` with `schema_migrations` tracking
- SQLite schema version: `v0` (`001_init_schema.sql`)
- DB initialization mode: `auto-apply migrations on backend startup`
- Seed loader: `backend/scripts/seed_db.py` (idempotent)
- Seed starter lexemes: `bog`, `kan`, `lide`
- Lookup service (checkpoint 8): lemma-aware classifier (`known` / `variation` / `new`)
- Analysis endpoint (checkpoint 9): `POST /api/analyze` with stable token list schema (documented in `docs/api-contract.md`)
- NLP adapter abstraction: `app/nlp/adapter.py`
- Danish NLP implementation: `DaCyLemmyNLPAdapter` in `app/nlp/danish.py`
- Default Danish NLP model: `da_dacy_small_tft-0.0.0` (`DANOTE_NLP_MODEL`)
- Key libraries:
  - `fastapi 0.116.1`
  - `uvicorn[standard] 0.35.0`
  - `spacy 3.8.11`
  - `dacy 1.1.4`
  - `lemmy 2.1.0`
  - `pytest 8.4.2` (test)
  - `httpx 0.28.1` (test client transport)
- NLP stack:
  - `spaCy` (core runtime)
  - `DaCy` (Danish pipeline)
  - `Lemmy` (lemmatization)
  - `sqlite3` (Python standard library driver for SQLite)
- spaCy compatibility command:
  - `python -m spacy download <pipeline_name>`
  - `python -m spacy validate`

## Dependency Locking Policy

- Lockfiles are required and must be committed to the repository.
- Frontend lockfile: `package-lock.json` (npm)
- Backend lockfile: `requirements.txt` + `requirements-dev.txt` (pinned)

## Current Lockfile Status

- Frontend lockfile present: `Yes` (`frontend/package-lock.json`)
- Backend lockfile present: `Yes` (`backend/requirements.txt`, `backend/requirements-dev.txt`)

Update this file whenever runtime versions or key dependencies change.
