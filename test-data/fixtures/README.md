# Fixture Pack

This directory stores regression fixtures and lemma benchmark inputs for prototype hardening.

## Layout

- `seed/starter_seed.json`: baseline seed lexemes used by regression setup.
- `notes/*.txt`: note text fixtures (short, medium, messy, punctuation-heavy, newline-heavy, mixed casing).
- `analysis-cases.json`: mapping of note fixtures to expected golden response files.
- `expected/analyze/*.json`: golden API outputs for `POST /api/analyze`.
- `lemma/*.json`: lemma-strength datasets grouped by category and test style.

## Extended Lemma Benchmark Set (Default)

- `lemma_tokens_by_category.extended.json`: 379 isolated-token lemma cases.
- `lemma_sentences_context.extended.json`: 102 sentence-context lemma cases.
- `classification_impact_variation.extended.json`: 391 product classification-impact cases.
- `lemma_robustness_noise.extended.json`: 75 robustness/noise cases.

## Typo Benchmark Set (Scaffold v1)

- `typo/typo_tokens_by_error_type.extended.json`: isolated-token typo cases by error family.
- `typo/typo_sentences_context.extended.json`: sentence-context typo cases.
- `typo/typo_classification_impact.extended.json`: status-decision impact cases (`typo_likely` / `uncertain` / `new` plus precedence guards).
- `typo/typo_robustness_noise.extended.json`: punctuation/noise/gating cases.
- `typo/typo_on_new_word_edge_cases.extended.json`: edge cases where true new words can resemble typos.

## Benchmark Reports

Benchmark runners append timestamped results to:

- `test-data/benchmark-reports/lemma-report.json`
- `test-data/benchmark-reports/typo-report.json`

Run:

```bash
cd /workspace/danote
PYTHONPATH=backend python scripts/run-lemma-benchmark.py
PYTHONPATH=backend python scripts/run-typo-benchmark.py
```

If model download is blocked in your environment, either:

- enable outbound network access to download `da_dacy_small_tft-0.0.0`, or
- run with degraded fallback explicitly:

```bash
PYTHONPATH=backend python scripts/run-lemma-benchmark.py --allow-degraded-nlp
PYTHONPATH=backend python scripts/run-typo-benchmark.py --allow-degraded-nlp
```

## Refresh Golden Outputs

Run:

```bash
cd /home/alejandro/Documents/github/danote/danote
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_fixture_goldens.py
```

Golden files will be regenerated under `test-data/fixtures/expected/analyze`.
