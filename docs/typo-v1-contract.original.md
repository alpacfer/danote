# Typo v1 Contract

This document defines the integration contract for adding typo detection to Danote v1.
It is the source of truth for backend/frontend alignment.

## Status Model (v1)

- `known`
- `variation`
- `typo_likely`
- `uncertain`
- `new`

## Precedence Rules (must hold)

1. Exact match in wordbank: `known`
2. Lemma-family match in wordbank: `variation`
3. Otherwise run typo engine:
   - high confidence: `typo_likely`
   - medium/ambiguous confidence: `uncertain`
   - weak/no evidence: `new`

`variation` always wins over typo signals. The typo engine is only evaluated after exact+lemma matching fails.

## Token Output Shape (v1)

For each finalized analyzed token, backend must return:

- `status`: one of the v1 statuses
- `surface`: original token text from note
- `normalized`: normalized comparison form
- `lemma`: lemma candidate when available, else `null`
- `suggestions`: list of suggestion objects (may be empty)
- `confidence`: numeric confidence score in range `[0.0, 1.0]`
- `reason_tags`: string list for debugging and telemetry

### Suggestion Object

- `value`: suggested replacement token
- `score`: numeric ranking score (0..1 preferred)
- `source_flags`: string list (examples: `from_symspell`, `from_hunspell`, `from_user_dict`)

## API Mapping Notes

Current `/api/analyze` v0 fields:
- `surface_token`
- `normalized_token`
- `lemma_candidate`
- `classification`
- `match_source`
- `matched_lemma`
- `matched_surface_form`

For v1 rollout:

- `classification` remains supported and should map to `status`
- `lemma_candidate` remains supported and should map to `lemma`
- new fields to add to each token payload:
  - `suggestions`
  - `confidence`
  - `reason_tags`

Frontend may use `status` directly if exposed, or continue using `classification` during transition.

## Action Contract (v1 UI behavior)

User actions supported from typo states:

- `replace`
- `add_as_new`
- `ignore`
- `dismiss`

These actions should be logged in `typo_feedback` with timestamp and shown suggestions.

## Non-Goals (v1)

- grammar correction
- phrase-level correction
- auto-replace while typing
- cloud or LLM correction in realtime

## Performance Contract (v1)

- Typing flow must remain non-blocking.
- Typo analysis runs on finalized tokens only.
- Unknown-token path should be cached and invalidated on lexeme/ignore/dictionary updates.

## Decision Safety Rules

- Never auto-apply corrections in v1.
- Proper noun/brand-like unknowns should bias to `uncertain` or `new`.
- If top candidate margin is weak, prefer `uncertain`.
