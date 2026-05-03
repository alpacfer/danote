# Word-entry preprocessing policy

danote preprocesses user text before lexical classification + action generation.

## Policy

All word-entry paths classifying/resolving words (`/api/analyze`, `/api/analyze/enrich-token` via `resolve_query`):

1. Strip inline `#` comments per line.
2. Normalize whitespace + case before lookup/classification.

## Why

Note analysis stripped inline comments; search/resolve paths used raw query text. Caused inconsistencies for inputs with `#` comments. Same preprocessing on both paths → predictable classification + action suggestions.

## Implementation references

- Shared helper: `backend/app/services/text_preprocessing.py`
- Analyze path use: `backend/app/services/use_cases/analyze.py`
- Resolve path use: `backend/app/services/use_cases/wordbank/core.py` and `backend/app/services/use_cases/wordbank/collaborators/cor_resolution.py`
