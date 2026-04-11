# Typo v1 Contract

Integration contract for typo detection in Danote v1. Source of truth for backend/frontend alignment.

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

`variation` always wins over typo signals. Typo engine evaluated only after exact+lemma matching fails.

## Token Output Shape (v1)

Each finalized analyzed token:

- `status`: one of the v1 statuses
- `surface`: original token text
- `normalized`: normalized comparison form
- `lemma`: lemma candidate or `null`
- `suggestions`: list of suggestion objects (may be empty)
- `confidence`: numeric `[0.0, 1.0]`
- `reason_tags`: string list for debugging/telemetry

### Suggestion Object

- `value`: suggested replacement token
- `score`: ranking score (0..1 preferred)
- `source_flags`: string list (e.g. `from_symspell`, `from_hunspell`, `from_user_dict`)

## API Mapping Notes

`/api/analyze` v0 fields: `surface_token`, `normalized_token`, `lemma_candidate`, `classification`, `match_source`, `matched_lemma`, `matched_surface_form`.

v1 rollout:
- `classification` remains supported, maps to `status`
- `lemma_candidate` remains supported, maps to `lemma`
- new fields: `suggestions`, `confidence`, `reason_tags`

Frontend may use `status` directly or continue using `classification` during transition.

## Action Contract (v1 UI behavior)

Actions: `replace`, `add_as_new`, `ignore`, `dismiss`. Logged in `typo_feedback` with timestamp and shown suggestions.

## Non-Goals (v1)

- grammar/phrase-level correction
- auto-replace while typing
- cloud/LLM realtime correction

## Performance Contract (v1)

- Typing flow non-blocking. Typo analysis on finalized tokens only.
- Unknown-token path cached; invalidated on lexeme/ignore/dictionary updates.

## Decision Safety Rules

- Never auto-apply corrections in v1.
- Proper noun/brand-like unknowns bias to `uncertain` or `new`.
- Weak top-candidate margin: prefer `uncertain`.
