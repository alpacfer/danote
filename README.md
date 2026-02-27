# danote

Language-learning note-taking web app (Danish-first) with a browser frontend and local Python backend.

## Project Structure

- `frontend/`: web app UI
- `backend/`: Python API, NLP pipeline, and SQLite access
- `docs/`: product definition, API contract, version tracking, test plan
- `scripts/`: development helper scripts
- `test-data/`: seed fixtures and sample sentences

## Run Instructions

## Developer Quickstart

```bash
cd <repo-root>
make setup
make lint
make test
```

For ongoing documentation/workflow verification:

```bash
cd <repo-root>
make docs-smoke
```

For AI-agent focused verification:

```bash
cd <repo-root>
make agent-verify
```

Agent-specific guidance:

- `AGENTS.md`
- `docs/agent-playbook.md`

One-command startup (recommended):

```bash
cd <repo-root>
./scripts/run-project.sh
```

This starts backend and frontend together, checks backend health, and stops both on `Ctrl+C`.

One-command setup for the pinned DaCy model `da_dacy_small_trf-0.2.0`:

```bash
cd <repo-root>
./scripts/setup-dacy-model.sh
```

This script installs system build prerequisites, recreates `backend/.venv`, installs
`backend/requirements.lock.txt`, installs the model wheel, and validates the model load.

Local workflow:

1. Start backend service.
2. Start frontend dev server.
3. Open the app in a browser and connect to local backend.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `python3-venv` / `python3-pip` are missing on Linux, bootstrap with `uv` first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --clear backend/.venv
~/.local/bin/uv pip install --python backend/.venv/bin/python -r backend/requirements.lock.txt
```

Frontend:

```bash
cd frontend
npm install
# optional if backend is not on default http://127.0.0.1:8000
# export VITE_BACKEND_URL=http://127.0.0.1:8000
npm run dev -- --host 127.0.0.1 --port 4173
```

Connectivity check:

- Frontend calls `GET /api/health` on startup.
- Backend returns readiness payload with `status: ok|degraded`.

Database init and seed:

- Backend startup auto-creates/migrates SQLite schema.
- Run idempotent seed loader:

```bash
cd backend
./.venv/bin/python scripts/seed_db.py
```

NLP compatibility check:

```bash
cd backend
./.venv/bin/python -m spacy validate
```

## Regression Baseline (Checkpoint 18)

Fixture pack:

- Notes and seed fixtures: `test-data/fixtures/`
- Golden analyze outputs: `test-data/fixtures/expected/analyze/`

Refresh golden outputs:

```bash
cd <repo-root>
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_fixture_goldens.py
```

Run fixture regression tests:

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/test_regression_fixtures.py -q
```

Run scripted e2e reliability flow:

```bash
cd <repo-root>
./scripts/e2e-regression.sh
```

Manual demo and release docs:

- `docs/manual-demo-script.md`
- `docs/release-checklist-prototype-v0.md`
- `docs/lemma-benchmark-baseline.md`
- `docs/lemma-benchmark-report-v0.md`

## Reproducibility

- Lockfiles must be committed when dependencies are introduced.
- Environment/runtime versions are tracked in `docs/versions.md`.


## Priority C references

- Backend dependency locking: `docs/backend-dependency-locking.md`
- ADR index: `docs/adr/README.md`
- Test pyramid + CI split: `docs/test-pyramid-and-ci.md`
