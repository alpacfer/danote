# Typo v1 Build Checklist (Repo-Specific)

Maps typo v1 plan to current Danote repo layout.

## 1) Contracts and config

- [x] `docs/typo-v1-contract.md`
- [x] `backend/app/core/typo_policy.v1.json`
- [x] `docs/typo-benchmark-schema-v1.md`

## 2) Database and migrations

Implement: new SQL migration in `backend/migrations/` (next version after `001_init_schema.sql`). Runner: `backend/app/db/migrations.py`.

Tables: `token_events`, `typo_feedback`, `ignored_tokens`.

Notes: `surface_forms` exists in schema v0. Add indexes for `normalized_token`, `token`, `timestamp`.

Tests: extend `backend/tests/db/test_db_schema.py`; add migration + insert/query tests per table.

## 3) Typo service module

Create: `backend/app/services/typo/__init__.py`, `typo_engine.py`, `gating.py`, `normalization.py`, `candidates.py`, `ranking.py`, `decision.py`, `cache.py` (optional first pass).

Primary interface: `TypoEngine.classify_unknown(...) -> TypoResult`

## 4) Classifier integration

Integrate in `backend/app/services/token_classifier.py`. Keep exact+lemma precedence. Call typo engine only on unresolved unknowns. Extend classification literals: `typo_likely`, `uncertain`.

Tests: extend `backend/tests/services/test_token_classifier_unit.py`, `test_token_classifier_integration.py`.

## 5) Analyze API schema update

Update: `backend/app/api/routes/analyze.py`, `docs/api-contract.md` (new v1 section, keep v0 compat).

Token fields to add: `suggestions`, `confidence`, `reason_tags`.

Tests: `backend/tests/api/test_analysis_endpoint.py` contract assertions.

## 6) Feedback and ignore API

Routes in `backend/app/api/routes/` (new `tokens.py` or extend `wordbank.py`), register in `backend/app/api/router.py`.

Endpoints: `POST /api/tokens/feedback`, `POST /api/tokens/ignore`.

Tests: near `backend/tests/api/test_wordbank_add_and_list_endpoint.py`.

## 7) Dictionary and candidate sources

Resources in `backend/resources/dictionaries/` (wordlists), loader in `backend/app/services/typo/candidates.py` or dedicated adapter.

Integrate: SymSpell candidate generation, Hunspell validity/fallback, user lexeme injection from DB.

## 8) Frontend status/action integration

Update: `frontend/src/App.tsx` + status badge/action components, API types in frontend data layer.

UI states: `typo_likely` -> Replace / Add as new / Ignore; `uncertain` -> Add as new / Ignore / optional suggestions.

Tests: `frontend/src/App.test.tsx` component behavior for new statuses/actions.

## 9) Benchmarks and fixtures

Scaffolded: `test-data/fixtures/typo/*.extended.json`.

Next: add `scripts/run-typo-benchmark.py` or extend `scripts/run-lemma-benchmark.py` with typo suite mode.

Metrics: precision/recall/F1, top-1/top-3 suggestion accuracy, status confusion matrix, latency p50/p95.

## 10) Recommended execution order

1. Gating + normalization + typo engine skeleton
2. SymSpell candidates
3. Ranking + decision thresholds
4. Token classifier + analyze API integration
5. Frontend display states
6. Feedback/ignore endpoints + frontend actions
7. Cache + perf tuning
8. Benchmark run + threshold tuning
