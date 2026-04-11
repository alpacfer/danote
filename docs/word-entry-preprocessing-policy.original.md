# Word-entry preprocessing policy

This document defines how danote preprocesses user-provided text before lexical classification and action generation.

## Policy

For all word-entry paths that classify or resolve words (`/api/analyze` and `/api/analyze/enrich-token` via `resolve_query`):

1. Strip inline comments introduced by `#` on each line.
2. Normalize whitespace and case before lookup/classification.

## Why

Historically, note analysis stripped inline comments, while search/resolve paths used raw query text.
This could cause subtle inconsistencies for inputs containing `#` comments.

Applying the same preprocessing behavior to both paths keeps classification and action suggestions predictable.

## Implementation references

- Shared helper: `backend/app/services/text_preprocessing.py`
- Analyze path use: `backend/app/services/use_cases/analyze.py`
- Resolve path use: `backend/app/services/use_cases/wordbank.py`
