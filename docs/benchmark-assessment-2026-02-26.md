# Benchmark assessment (2026-02-26, consolidated best typo strategy)

Commands run from repository root:

```bash
PYTHONPATH=backend:scripts python scripts/run-typo-benchmark.py --allow-degraded-nlp --dictionary-mode combined
PYTHONPATH=backend:scripts python scripts/run-typo-benchmark.py --allow-degraded-nlp --dictionary-mode base
```

## Consolidation decision

To reduce complexity, we kept only the typo decisioning path that has reported the best status performance in this repository:

- blended confidence (raw score + top-2 posterior stabilizer)
- mild prior-aware threshold calibration
- distance-1 high-likelihood promotion

We removed extra runtime branching/configuration for alternative boost variants and kept one default path in code.

## Latest benchmark results

| Mode | Status accuracy | Top-1 accuracy | Macro-F1 |
|---|---:|---:|---:|
| combined | **46.1%** | **83.0%** | **46.2%** |
| base | **12.1%** | **10.4%** | **13.3%** |

## Comparison to earlier reference points

- Previous strong combined baseline: **40.5%** status accuracy.
- Current consolidated strategy: **46.1%** status accuracy (+5.6 pp).

## Artifact

- Updated benchmark report: `test-data/benchmark-reports/typo-report.json`
