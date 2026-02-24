# Lemma Benchmark Baseline (Checkpoint 18)

## Purpose

Track lemma recognition strength by category before adding typo and phrase features.

## Fixture Sources

- `test-data/fixtures/lemma/lemma_tokens_by_category.json`
- `test-data/fixtures/lemma/lemma_sentences_context.json`
- `test-data/fixtures/lemma/classification_impact_variation.json`
- `test-data/fixtures/lemma/lemma_robustness_noise.json`

## MVB Scope (Current)

- Token lemma cases: `60`
- Sentence-context lemma cases: `20`
- Classification-impact cases: `30`
- Robustness/noise cases: `10`

## Frozen Policies

- Case normalization for DB lookup: `enabled` (case-insensitive behavior)
- Punctuation tolerance for benchmark single-token robustness cases: `enabled` (edge punctuation stripped)

## Run Benchmark

```bash
cd /home/alejandro/Documents/github/danote/danote
PYTHONPATH=backend backend/.venv/bin/python scripts/run-lemma-benchmark.py
```

## Metrics to Track

- Exact lemma accuracy (overall and per category)
- Lemma coverage (lemma returned vs missing)
- Context gain (sentence-context minus isolated-token accuracy)
- Variation classification accuracy
- False variation rate
- False new rate

## Category Slices

- noun regular / irregular
- verb regular / irregular / modal
- adjective inflection / degree
- compounds
- diacritics
- punctuation-attached tokens
- robustness noise

## Reporting Template

1. Overall summary
   - Total lemma cases
   - Exact lemma accuracy
   - Coverage
   - Variation classification accuracy
2. Per-category breakdown
   - Category name, count, accuracy, notable failure patterns
3. Top failure examples
   - surface, predicted lemma, expected lemma, category, likely cause
4. Prototype decision
   - good enough / good enough with limitations / needs fixes

## Pass/Fail Guidance

- Hard fail: crashes, unstable token handling, frequent false `variation` on clearly new words.
- Expected baseline pass: canonical flows stable (`bog`, `bogen`, `kat`) and no crash on noisy notes.
