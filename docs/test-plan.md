# Test Plan

## Backend

### Unit (`backend/tests`)

- `test_smoke.py`: app imports and starts.
- `test_health.py`: health route shape and readiness payload.
- `test_token_classifier_unit.py`: normalization and classification logic.
- `test_nlp_adapter_unit.py`: adapter behavior with mocked internals.

### Integration (`backend/tests`)

- `test_db_schema.py`: migration, seed idempotency, uniqueness constraints.
- `test_token_classifier_integration.py`: seeded DB + real NLP + classifier matrix.
- `test_nlp_adapter_integration.py`: lemma behavior for Danish forms and safety cases.
- `test_nlp_startup_integration.py`: NLP startup metadata and loading.
- `test_analysis_endpoint.py`: analyze endpoint behavior and token filtering.
- `test_wordbank_endpoint.py`: add-word insert and duplicate handling.
- `test_reliability.py`: restart persistence and degraded-mode failure handling.
- `test_regression_fixtures.py`: fixture-to-golden regression checks.

### Contract (`backend/tests`)

- `test_analysis_endpoint.py::test_response_matches_contract_schema_exactly`
- Health and failure contract checks in `test_health.py` and `test_reliability.py`.

## Frontend

### Components/Rendering (`frontend/src/App.test.tsx`)

- Shell render, header, tabs, status badge, legend, table states.

### Behavior (`frontend/src/App.test.tsx`)

- Debounce, stale-response protection, finalized-token gating.

### Integration (`frontend/src/App.test.tsx`)

- Analyze API mocked flows.
- Add-word API mocked flows (success/error + refresh).
- Backend degraded/offline badge handling.

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
- MVB lemma set sizes: tokens `60`, sentence-context `20`, classification impact `30`, robustness `10`.

## Before Tagging Prototype

1. Run backend suite.
2. Run frontend suite.
3. Run fixture regression test.
4. Run `scripts/e2e-regression.sh`.
5. Execute manual demo checklist.
