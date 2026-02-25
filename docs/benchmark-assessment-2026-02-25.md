# Benchmark assessment (2026-02-25)

Commands run from repository root:

```bash
PYTHONPATH=backend python scripts/run-typo-benchmark.py
PYTHONPATH=backend python scripts/run-lemma-benchmark.py
```

## Typo benchmark (expanded)

- Token typo fixture size: **500** cases (expanded from 10)
- Total typo benchmark cases (token + context + classification + edge): **519**
- This now exceeds the lemma benchmark total (**481**) as requested.
- Status accuracy: **35/519 (6.7%)**
- Top-1 accuracy (token set): **52/500 (10.4%)**
- Report path: `test-data/benchmark-reports/typo-report.json`

## Lemma benchmark

- Lemma accuracy: **459/481 (95.4%)**
- Lemma coverage: **481/481 (100.0%)**
- Token-only lemma accuracy: **359/379 (94.7%)**
- Sentence-context lemma accuracy: **100/102 (98.0%)**
- Context gain: **+3.3 pp**
- Classification impact accuracy: **387/391 (99.0%)**
- Robustness pass rate: **73/75 (97.3%)**
- Report path: `test-data/benchmark-reports/lemma-report.json`

## Accuracy assessment

- **Benchmark breadth target met**: typo suite now includes more total evaluated cases than the lemma suite.
- **Current typo accuracy is very low on the expanded corpus**: 6.7% status accuracy indicates major gaps in typo-status calibration/label expectations at larger vocabulary scale.
- **Top-1 typo suggestion quality is also low at scale**: 10.4% on the expanded token set.
- **Lemma pipeline remains strong and stable**: 95.4% lemma accuracy with 100% coverage, 99.0% classification accuracy, and 97.3% robustness.
