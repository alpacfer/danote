# Lemma Benchmark Report v0

Date: 2026-02-24

## Run Command

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/run-lemma-benchmark.py
```

## Summary

- Lemma accuracy: `70/80` (`87.5%`)
- Lemma coverage: `80/80` (`100.0%`)
- Token-only lemma accuracy: `51/60` (`85.0%`)
- Sentence-context lemma accuracy: `19/20` (`95.0%`)
- Context gain: `+10.0 pp`
- Classification impact accuracy: `28/30` (`93.3%`)
- Variation accuracy: `13/15` (`86.7%`)
- False variation rate (expected `new` -> predicted `variation`): `0.0%`
- False new rate (expected `variation` -> predicted `new`): `13.3%`
- Robustness pass rate: `10/10` (`100.0%`)

## Per-Category Snapshot

- Lemma categories:
  - `noun_regular`: `13/15` (`86.7%`)
  - `noun_irregular`: `9/10` (`90.0%`)
  - `adjective`: `10/10` (`100.0%`)
  - `verb_regular`: `11/15` (`73.3%`)
  - `verb_irregular_modal`: `8/10` (`80.0%`)
  - `participle_aux`: `8/8` (`100.0%`)
  - `adjective_adverb`: `5/6` (`83.3%`)
  - `lesson_style`: `6/6` (`100.0%`)
- Classification/robustness categories:
  - `exact_known`: `10/10` (`100.0%`)
  - `variation`: `13/15` (`86.7%`)
  - `new_guard`: `5/5` (`100.0%`)
  - `punctuation_attached`: `4/4` (`100.0%`)
  - `casing`: `2/2` (`100.0%`)
  - `whitespace_newline`: `2/2` (`100.0%`)
  - `typo_guard`: `2/2` (`100.0%`)

## Initial Notes

- Canonical prototype cases (`bog`, `bogen`, `kat`) remain stable.
- Main misses are in some regular verb and irregular/modal forms (`spist`, `arbejdet`, `snakket`, `været`, `gået`).
- Two variation classification misses in this set: `bøgerne` and `gået` were predicted `new`.
- Robustness baseline is stable (no crashes, punctuation/casing/whitespace behavior passed under frozen policies).
