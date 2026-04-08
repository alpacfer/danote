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
- `tests/use_cases/` — orchestration, DB interactions, service calls
- `tests/services/` — pure domain logic, transformations
- `tests/api/` — HTTP status codes and response shape only, never business logic

**Required patterns:**
- `from __future__ import annotations` at top of every test file
- Inject dependencies via constructor — never mock internals with `unittest.mock.patch`
- `_db_path(tmp_path)` from `tests/helpers/factories.py` for isolated DB paths
- `FakeNLPAdapter` / `StubNLPAdapter` from `tests/helpers/fakes.py` — never instantiate real NLP in unit tests
- Session-level file snapshots (e.g., `gemini-applied-changes.jsonl`) are auto-restored via `conftest.py` — don't add extra cleanup

**Naming:** `test_<what>_<condition>_<expected_outcome>`

## Frontend (Vitest + RTL)

Run tests:
```bash
cd frontend && npx vitest run src/test/path/to/file.test.tsx
```

**Required patterns:**
- Import test utilities from `@/test/app-test-helpers` — do not import from `@testing-library/react` directly
- `renderApp()` for full integration tests; use focused component renders only for isolated unit tests
- `mockFetchImplementation({ analyzeTokens: [...] })` to stub backend responses
- `vi.useRealTimers()` for async timing tests
- Test user-observable DOM behavior — not internal hook state or implementation details

**Test file location:** `frontend/src/test/` — mirror the source structure
