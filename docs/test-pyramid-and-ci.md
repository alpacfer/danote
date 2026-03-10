# Test Pyramid and CI Pipeline Split

## Test layers

1. **Fast layer (PR default)**
   - Frontend lint + tests
   - Backend fast unit + API tests
   - Docs smoke checks

2. **Medium layer (PR default)**
   - Backend integration/reliability subset:
     - `tests/system/test_reliability.py`

3. **Slow layer (manual/scheduled)**
   - Backend regression fixture tests:
     - `tests/system/test_regression_fixtures.py`

## Local command mapping

```bash
make lint
make test
make docs-smoke
```

Medium checks:

```bash
bash ./scripts/pytest-backend.sh -q tests/system/test_reliability.py
```

Slow checks:

```bash
bash ./scripts/pytest-backend.sh -q tests/system/test_regression_fixtures.py
```
