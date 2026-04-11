---
paths:
  - "backend/tests/**"
  - "frontend/src/test/**"
---

# Testing rules

## Backend (pytest)

Run tests:
```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/path/to/test_file.py
```

**Layer placement:**
- `tests/use_cases/` — orchestration, DB, service calls
- `tests/services/` — pure domain logic, transformations
- `tests/api/` — HTTP codes + response shape only, no business logic

**Required patterns:**
- `from __future__ import annotations` top of every test file
- Inject via constructor — never mock internals with `unittest.mock.patch`
- `_db_path(tmp_path)` from `tests/helpers/factories.py` — isolated DB paths
- `FakeNLPAdapter` / `StubNLPAdapter` from `tests/helpers/fakes.py` — no real NLP in unit tests
- Session-level snapshots (e.g., `gemini-applied-changes.jsonl`) auto-restored via `conftest.py` — no extra cleanup

**Naming:** `test_<what>_<condition>_<expected_outcome>`

## Frontend (Vitest + RTL)

Run tests:
```bash
cd frontend && npx vitest run src/test/path/to/file.test.tsx
```

**Required patterns:**
- Import utils from `@/test/app-test-helpers` — never from `@testing-library/react`
- `renderApp()` for full integration tests; focused renders for isolated unit tests
- `mockFetchImplementation({ analyzeTokens: [...] })` stub backend responses
- `vi.useRealTimers()` async timing tests
- Test observable DOM behavior — not hook state or impl details

**Test file location:** `frontend/src/test/` — mirror source structure