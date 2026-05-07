# `backend/app/db/repositories/`

SQLite data access. One file per table or domain area, split by read/write where size warrants.

## File map

| File | Role |
|---|---|
| `wordbank.py` | Top-level wordbank entry; small adapters / shared helpers. |
| `wordbank_reads.py` | Query-only operations on wordbank tables. |
| `wordbank_mutations.py` | Insert / update / delete on wordbank tables. |
| `wordbank_search.py` | Search-specific queries (fuzzy, surface form). |
| `wordbank_surface_form_queries.py` | Surface-form lookups used by search and verification. |
| `wordbank_change_log.py` | Audit/history tracking for wordbank edits. |
| `wordbank_category_reads.py` / `wordbank_category_mutations.py` | Category sub-domain. |
| `wordbank_background_jobs.py` | Background-job state for async wordbank work. |
| `wordbank_models.py` | Repository-layer dataclasses (not API DTOs). |
| `sentencebank.py` | Sentencebank read + write (single file; smaller domain). |
| `numbers_audio.py`, `presaved_words_audio.py` | Audio cache lookups. |

## Rules

- Use-cases call repositories; routes do not.
- API DTOs do not live here — see `api/schemas/v1/`.
- For new wordbank queries, prefer `wordbank_reads.py` unless it's clearly search-specific or surface-form-specific.
- Test DB behavior under `backend/tests/db/`. Use `_db_path(tmp_path)` for isolated paths.
