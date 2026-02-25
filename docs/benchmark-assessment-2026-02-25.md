# Benchmark assessment (2026-02-25)

Commands run from repository root:

```bash
PYTHONPATH=backend:scripts python scripts/run-typo-benchmark.py --allow-degraded-nlp --dictionary-mode base
PYTHONPATH=backend:scripts python scripts/run-typo-benchmark.py --allow-degraded-nlp --dictionary-mode combined
```

## Typo benchmark comparison (base vs combined dictionaries)

- Token typo fixture size: **500** cases.
- Total typo benchmark cases: **519**.
- Base dictionary mode (`da_words.txt` only):
  - Status accuracy: **50/519 (9.6%)**.
  - Top-1 accuracy (token set): **52/500 (10.4%)**.
- Combined dictionary mode (`da_words.txt` + `dsdo.txt`):
  - Status accuracy: **210/519 (40.5%)**.
  - Top-1 accuracy (token set): **416/500 (83.2%)**.

## Improvement assessment

- Combined dictionaries remain the strongest setup for typo correction quality.
- Relative to base mode, combined mode gives:
  - **+30.9 pp** status accuracy (9.6% → 40.5%).
  - **+72.8 pp** top-1 token accuracy (10.4% → 83.2%).
- Relative to the prior combined run (38.5%), the latest calibration pass improved status accuracy to **40.5%** while holding top-1 accuracy at **83.2%**.

## What changed in this iteration

- Decision thresholds are now loaded from `typo_policy.v1.json` and tuned (`typo_likely=0.78`, `uncertain=0.50`, `margin=0.08`) to reduce over-conservative `new` classifications.
- Ignored-token checks are now cached in-memory after first load, and updated on `add_ignored_token`, reducing repeated DB reads on hot paths.

## Notes

- Benchmark report path: `test-data/benchmark-reports/typo-report.json`.
- The benchmark run emitted a spaCy model compatibility warning (model trained on older spaCy), which did not block execution.
