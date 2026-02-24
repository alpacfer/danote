# Lemma Benchmark Report v0

Date: 2026-02-24

## Run Command

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run-lemma-benchmark.py
```

## Summary

- Lemma accuracy: `9/11` (`81.8%`)
- Classification impact accuracy: `3/3` (`100.0%`)
- Robustness pass rate: `4/4` (`100.0%`)

## Per-Category Snapshot

- `adjective_degree`: `1/1` (`100.0%`)
- `classification_impact`: `3/3` (`100.0%`)
- `compound`: `1/1` (`100.0%`)
- `diacritics`: `0/1` (`0.0%`)
- `noun_irregular`: `1/1` (`100.0%`)
- `noun_regular`: `1/1` (`100.0%`)
- `robustness`: `4/4` (`100.0%`)
- `robustness_punctuation`: `1/1` (`100.0%`)
- `sentence_context`: `2/3` (`66.7%`)
- `verb_irregular`: `1/1` (`100.0%`)
- `verb_modal`: `1/1` (`100.0%`)

## Initial Notes

- Canonical prototype cases (`bog`, `bogen`, `kat`) are stable.
- Diacritic and sentence-context slices need expansion and closer inspection before typo/phrase work.
- No crash behavior observed in noise fixtures.
