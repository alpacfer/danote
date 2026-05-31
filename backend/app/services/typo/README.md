# Typo & Spelling Correction Engine

This directory contains the core services and logic for detecting typos and providing fuzzy spelling corrections in Danish and English.

## File Map

- `typo_engine.py`: Orchestrator that integrates gating, candidate generation, ranking, and final decisions.
- `gating.py`: Gating rules to bypass checks for numbers, acronyms, URLs, or casing styles.
- `normalization.py`: Case and diacritic normalization for uniform comparisons.
- `candidates.py`: Candidate generator using local dictionary lookups within bounded edit distances.
- `ranking.py`: Advanced candidate ranker utilizing Levenshtein distance, keyboard adjacency layout weights, and frequency priors.
- `decision.py`: Final suggestion selector implementing proper-noun bias and confidence gates.
- `cache.py`: High-performance cache for spelling results and user-ignored typos.
