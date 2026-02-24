# Typo v1 Build Checklist (Repo-Specific)

This checklist maps the typo v1 plan to the current Danote repository layout.

## 1) Contracts and config

- [x] Add contract doc: `docs/typo-v1-contract.md`
- [x] Add policy config scaffold: `backend/app/core/typo_policy.v1.json`
- [x] Add typo fixture schema doc: `docs/typo-benchmark-schema-v1.md`

## 2) Database and migrations

Implement in:
- new SQL migration in `backend/migrations/` (next version after `001_init_schema.sql`)
- migration runner already exists in `backend/app/db/migrations.py`

Tables to add:
- `token_events`
- `typo_feedback`
- `ignored_tokens`

Notes:
- `surface_forms` already exists in schema v0.
- Add indexes for frequent lookups (`normalized_token`, `token`, `timestamp`).

Tests:
- extend `backend/tests/test_db_schema.py`
- add migration + insert/query tests for each new table

## 3) Typo service module

Create:
- `backend/app/services/typo/__init__.py`
- `backend/app/services/typo/typo_engine.py`
- `backend/app/services/typo/gating.py`
- `backend/app/services/typo/normalization.py`
- `backend/app/services/typo/candidates.py`
- `backend/app/services/typo/ranking.py`
- `backend/app/services/typo/decision.py`
- `backend/app/services/typo/cache.py` (optional first pass)

Primary interface:
- `TypoEngine.classify_unknown(...) -> TypoResult`

## 4) Classifier integration

Integrate in:
- `backend/app/services/token_classifier.py`

Required behavior:
- keep exact and lemma precedence unchanged
- only call typo engine on unresolved unknowns
- extend classification literals to include `typo_likely` and `uncertain`

Tests:
- extend `backend/tests/test_token_classifier_unit.py`
- extend `backend/tests/test_token_classifier_integration.py`

## 5) Analyze API schema update

Update:
- `backend/app/api/routes/analyze.py`
- `docs/api-contract.md` (new v1 section while keeping v0 compatibility)

Add token fields:
- `suggestions`
- `confidence`
- `reason_tags`

Tests:
- `backend/tests/test_analysis_endpoint.py` contract assertions

## 6) Feedback and ignore API

Add routes in:
- `backend/app/api/routes/` (new file `tokens.py` or extend `wordbank.py`)
- register in `backend/app/api/router.py`

Endpoints:
- `POST /api/tokens/feedback`
- `POST /api/tokens/ignore`

Tests:
- new API tests near `backend/tests/test_wordbank_endpoint.py`

## 7) Dictionary and candidate sources

Implement resources in:
- `backend/resources/dictionaries/` (wordlists)
- loader in `backend/app/services/typo/candidates.py` (or dedicated adapter)

Integrate:
- SymSpell candidate generation
- Hunspell validity/fallback
- user lexeme injection from DB

## 8) Frontend status/action integration

Update:
- `frontend/src/App.tsx` and status badge/action components
- API types in frontend data layer

Add UI states:
- `typo_likely`: Replace / Add as new / Ignore
- `uncertain`: Add as new / Ignore / optional suggestions

Tests:
- `frontend/src/App.test.tsx` component behavior for new statuses/actions

## 9) Benchmarks and fixtures

Already scaffolded:
- `test-data/fixtures/typo/*.extended.json`

Next:
- add runner script `scripts/run-typo-benchmark.py`
- or extend `scripts/run-lemma-benchmark.py` with typo suite mode

Metrics:
- precision/recall/F1 for typo detection
- top-1 and top-3 suggestion accuracy
- status confusion matrix
- latency p50/p95

## 10) Recommended execution order

1. Gating + normalization + typo engine skeleton
2. SymSpell candidates
3. Ranking + decision thresholds
4. Token classifier + analyze API integration
5. Frontend display states
6. Feedback/ignore endpoints + frontend actions
7. Cache + perf tuning
8. Benchmark run + threshold tuning
