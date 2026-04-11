# Test Plan

## Backend

### Fast backend groups

- `tests/use_cases/`: use-case orchestration and workflow behavior.
- `tests/services/`: service units and focused service integrations.
- `tests/bootstrap/`: runtime/config/bootstrap behavior.
- `tests/db/`: schema, fixture pack, and repository persistence checks.
- `tests/api/`: HTTP contract and endpoint behavior.

### System backend groups

- `tests/system/test_reliability.py`: restart persistence and degraded-mode failure handling.
- `tests/system/test_analysis_endpoint_real_nlp.py`: real-model `/api/analyze` smoke coverage kept out of the fast API tier.
- `tests/system/test_regression_fixtures.py`: fixture-to-golden regression checks.
- `tests/system/test_wordbank_performance_smoke.py`: opt-in performance smoke coverage.

### Contract

- `tests/api/test_analysis_endpoint.py::test_response_matches_contract_schema_exactly`
- Health and failure contract checks in `tests/api/test_health.py` and `tests/system/test_reliability.py`.

## Frontend

### Components/Rendering (`frontend/src/test/app/*.test.tsx`)

- Shell render, header, tabs, status badge, legend, table states.

### Behavior (`frontend/src/test/app/*.test.tsx`)

- Debounce, stale-response protection, finalized-token gating.

### Integration (`frontend/src/test/app/*.test.tsx`)

- Analyze API mocked flows.
- Add-word API mocked flows (success/error + refresh).
- Backend degraded/offline badge handling.

### Wordbank/Search test classification

- `renderer-only`: frontend render from typed fixtures; no backend semantics claimed.
- `request-shape`: request bodies, optimistic hydration, polling, transition behavior.
- `contract`: backend use-case/API tests pinning `LemmaDetailsResponse`, `AddWordResponse.saved_snapshot`, `ResolveQueryResponse.word_actions`.
- `round-trip`: backend flows saving search-seeded lemma, reading word page/details payload.
- Shared frontend contract fixtures: `frontend/src/test/app/wordbank-contract-fixtures.ts`.

## End-to-End (E2E)

- Scripted backend flow: `scripts/e2e-regression.sh`
  - startup + health
  - canonical analyze
  - add word
  - backend restart
  - persistence re-check
- Manual browser flow: `docs/manual-demo-script.md`

## Fixture Baseline

- Fixture sources: `test-data/fixtures/`.
- Golden outputs: `test-data/fixtures/expected/analyze/*.json`.
- Golden refresh tool: `scripts/generate_fixture_goldens.py`.
- Lemma benchmark runner: `scripts/run-lemma-benchmark.py`.
- Translation benchmark runner (word-only): `scripts/run-translation-benchmark.py`.
- MVB lemma set sizes: tokens `60`, sentence-context `20`, classification impact `30`, robustness `10`.

Run benchmark scripts with the repo venv interpreter:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run-translation-benchmark.py
```

## Before Tagging Prototype

1. Run backend suite.
2. Run frontend suite.
3. Run fixture regression test.
4. Run `scripts/e2e-regression.sh`.
5. Execute manual demo checklist.