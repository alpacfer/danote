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

## Refresh Golden Outputs

Run:

```bash
cd /home/alejandro/Documents/github/danote/danote
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_fixture_goldens.py
```

Golden files will be regenerated under `test-data/fixtures/expected/analyze`.
