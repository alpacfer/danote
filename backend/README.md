# Backend

Python API service for danote.

## Stack

- Framework: FastAPI
- ASGI server: Uvicorn
- Config/logging: standard library modules (`os`, `pathlib`, `logging`)
- Database driver: `sqlite3` from Python standard library

## Database (Checkpoint 5)

- DB file: `backend/data/danote.sqlite3` (default; configurable via `DANOTE_DB_PATH`)
- Migration strategy: versioned SQL files in `backend/migrations/`
- Applied migrations tracking table: `schema_migrations`
- Schema v0 tables:
  - `lexemes` (unique lemma/base form)
  - `surface_forms` (optional inflected/typed forms linked to lexeme)
- Startup behavior: migrations are auto-applied when backend starts

### Seed Data

Seed script (idempotent):

```bash
cd backend
./.venv/bin/python scripts/seed_db.py
```

Starter seed includes lexemes used by tests and prototype examples:

- `bog`
- `kan`
- `lide`

## NLP (Checkpoint 7)

- Abstraction: `app/nlp/adapter.py` (`NLPAdapter` protocol)
- Danish implementation: `app/nlp/danish.py` (`DaCyLemmyNLPAdapter`)
- Components:
  - DaCy model pipeline for tokenization/POS/morphology access
  - Lemmy for POS-aware Danish lemmatization
- Startup behavior:
  - NLP pipeline is loaded during app startup
  - startup logs include loaded NLP adapter + model + package versions

### NLP Model and Compatibility

Default model configured by `DANOTE_NLP_MODEL`:

- `da_dacy_small_tft-0.0.0`

Compatibility check command:

```bash
cd backend
./.venv/bin/python -m spacy validate
```

Runtime note:

- On backend startup, the adapter validates loaded model metadata against runtime spaCy and logs
  `nlp_model_spacy_version_mismatch` when incompatible (includes model name + version spec + runtime version).
- If incompatibility is reported, align runtime/model versions before relying on benchmark-quality lemma behavior.

## Environment Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock.txt
```

If your Linux image is missing `python3-venv` / `python3-pip`, use `uv` (no sudo required):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --clear .venv
~/.local/bin/uv pip install --python .venv/bin/python -r requirements.lock.txt
```

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## API

- `GET /api/` -> scaffold status
- `GET /api/health` -> readiness payload (`ok` or `degraded`)
- `POST /api/analyze` -> note token classification response
- `POST /api/wordbank/lexemes` -> manual add-to-wordbank

## Domain Service (Checkpoint 8)

- Lemma-aware token classification service: `app/services/token_classifier.py`
- Input: single finalized token string
- Output: structured classification result with metadata
- Classification rules (v0):
  - exact match in DB -> `known`
  - else lemma exists in lexeme DB -> `variation`
  - else -> `new`
- Metadata includes: surface token, normalized token, lemma candidate, match source (`exact` | `lemma` | `none`)

## Test

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest
```

Fixture regression subset:

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/test_regression_fixtures.py -q
```


Dependency lock policy:

- Canonical backend install file: `requirements.lock.txt`.
- Refresh lock file with `../scripts/sync-backend-lock.sh` when dependency inputs change.
- See `../docs/backend-dependency-locking.md` for details.
