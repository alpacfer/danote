# Test Pyramid and CI Pipeline Split

## Test layers

1. **Fast layer (PR default)**
   - Frontend lint + tests
   - Backend fast unit tests
   - Docs smoke checks

2. **Medium layer (PR default)**
   - Backend integration/reliability subset:
     - `tests/test_reliability.py`
     - `tests/test_wordbank_endpoint.py`

3. **Slow layer (manual/scheduled)**
   - Backend regression fixture tests:
     - `tests/test_regression_fixtures.py`

## Local command mapping

```bash
make lint
make test
make docs-smoke
```

Medium checks:

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_reliability.py tests/test_wordbank_endpoint.py
```

Slow checks:

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_regression_fixtures.py
```
