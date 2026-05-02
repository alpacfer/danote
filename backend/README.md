# Backend

Python API service for danote.

## Stack

- Framework: FastAPI
- ASGI server: Uvicorn
- Config/logging: standard library modules (`os`, `pathlib`, `logging`)
- Database driver: `sqlite3` from Python standard library
- Translation: DeepL API (default) or Azure Translator Text API
- Text-to-speech: Azure Speech SDK

## Current schema overview

- DB file: `backend/data/danote.sqlite3` (default; configurable via `DANOTE_DB_PATH`)
- Applied migrations tracking table: `schema_migrations`
- Startup behavior: migrations are auto-applied when backend starts

Major schema domains (high-level):

- Core lexicon:
  - `lexemes` stores canonical lemmas and shared lexical metadata
  - `surface_forms` stores observed/inflected forms linked to lexemes (and optional meaning linkage)
  - `lexeme_meanings` stores meaning sections/senses and optional COR lemma references
  - `wordbank_categories` stores the shared semantic category catalog used by Gemini classification
  - `wordbank_category_assignments` stores semantic category badges for lemma-root and meaning-section scopes
- Typo and feedback telemetry:
  - `token_events` records token-level classification outcomes
  - `typo_feedback` captures user decisions on suggestions
  - `ignored_tokens` stores opt-out tokens/scopes
- Sentence bank:
  - `sentence_bank` stores normalized source sentences with optional cached translations
- Phrase translation cache:
  - `phrase_translations` caches phrase-level translations by source phrase
- COR variant linkage:
  - `surface_form_cor_variants` links stored surface forms to COR IDs for lookup alignment
- Background jobs:
  - `wordbank_background_jobs` stores durable async job state for wordbank workflows

Schema evolution is migration-driven: the authoritative source of truth is the ordered SQL files in
[`backend/migrations/`](./migrations/), which should be read sequentially for exact DDL and history.

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

## NLP (retired)

- Abstraction: `app/nlp/adapter.py` (`NLPAdapter` protocol)
- Previous stack: DaCy/spaCy/Lemmy with `da_dacy_small_trf-0.2.0`
- Startup behavior:
  - `DANOTE_NLP_ENABLED` defaults to `0`
  - no DaCy model is installed, validated, or loaded by default
  - `/api/analyze` is unavailable unless a future NLP adapter is added and enabled

### COR Lexicon Search

- Command search uses a local COR SQLite file built from
  `backend/resources/dictionaries/cor1.5.1.0.tsv`.
- Command-search endpoints:
  - `GET /api/wordbank/search/cor-form?form=<word>&limit=<n>`
  - `GET /api/wordbank/search/cor-lemma/{lemma_idx}?limit=<n>`
- Search endpoint behavior:
  - Danish-only lookup
  - no translation calls
  - no DaCy dependency
  - grouped analyses by `(lemma, gloss, pos)` with per-variant morphology metadata
- `resolve-query` remains available for non-command-search flows.
- Runtime flags:
  - `DANOTE_COR_LOOKUP_ENABLED=1` (default when using env-based `load_settings`)
  - `DANOTE_COR_LOOKUP_TIMEOUT_SECONDS=4.0`
  - `DANOTE_COR_LOCAL_DB_PATH=backend/resources/dictionaries/cor.sqlite`

Build/update local COR SQLite:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/build_cor_sqlite.py \
  --input resources/dictionaries/cor1.5.1.0.tsv \
  --output resources/dictionaries/cor.sqlite
```

When a new COR TSV version arrives, rerun the build command and replace the
shipped `cor.sqlite`.

Build/update local English SQLite:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/build_english_sqlite.py \
  --input resources/dictionaries/english_wiki.jsonl \
  --output resources/dictionaries/english_wiki.sqlite
```

The English lookup flow reads `english_wiki.sqlite` via `DANOTE_EN_LOCAL_DB_PATH`
and uses `english_wiki.jsonl` as the rebuild source.

## Environment Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock.txt
```

Search-only setup (the default backend install has no DaCy model):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.search.txt
export DANOTE_NLP_ENABLED=0
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
export DANOTE_TRANSLATION_PROVIDER="deepl"
export DANOTE_TRANSLATION_DEEPL_API_KEY="your-deepl-key"
export DANOTE_TTS_AZURE_API_KEY="your-speech-key"
export DANOTE_TTS_AZURE_REGION="your-speech-region"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Configuration reference: [`../docs/reference/configuration-reference.md`](../docs/reference/configuration-reference.md).

### Configuration precedence

Backend settings are resolved in this order:

1. exported environment variables
2. `<repo-root>/.env.local`
3. hardcoded defaults in `backend/app/core/config.py`

For the complete variable catalog (defaults, accepted values, and fallback/alias behavior), see [`../docs/reference/configuration-reference.md`](../docs/reference/configuration-reference.md).

## API

- `GET /api/` -> scaffold status
- `GET /api/health` -> readiness payload (`ok` or `degraded`)
- `POST /api/analyze` -> disabled unless a future NLP adapter is configured
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
bash ./scripts/pytest-backend.sh
```

Fixture regression subset is retired while DaCy NLP is disabled.

Fast backend suite:

```bash
make test-backend-fast
```

Interactive shell convenience:

```bash
export PATH="$(pwd)/backend/.venv/bin:$PATH"
```


Dependency lock policy:

- Canonical backend install file: `requirements.lock.txt`.
- Refresh lock file with `../scripts/sync-backend-lock.sh` when dependency inputs change.
- See `../docs/architecture/backend-dependency-locking.md` for details.
