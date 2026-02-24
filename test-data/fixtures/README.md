# Fixture Pack

This directory stores regression fixtures and lemma benchmark inputs for prototype hardening.

## Layout

- `seed/starter_seed.json`: baseline seed lexemes used by regression setup.
- `notes/*.txt`: note text fixtures (short, medium, messy, punctuation-heavy, newline-heavy, mixed casing).
- `analysis-cases.json`: mapping of note fixtures to expected golden response files.
- `expected/analyze/*.json`: golden API outputs for `POST /api/analyze`.
- `lemma/*.json`: lemma-strength datasets grouped by category and test style.

## Refresh Golden Outputs

Run:

```bash
cd /home/alejandro/Documents/github/danote/danote
PYTHONPATH=backend backend/.venv/bin/python scripts/generate_fixture_goldens.py
```

Golden files will be regenerated under `test-data/fixtures/expected/analyze`.
