# Typo Benchmark Schema v1

v1 typo fixture format + policy config format. Same conventions as `test-data/fixtures/lemma/*.json`: flat JSON arrays with stable `id`, `category`, explicit expected outputs.

## Fixture Files

- `test-data/fixtures/typo/typo_tokens_by_error_type.extended.json`
- `test-data/fixtures/typo/typo_sentences_context.extended.json`
- `test-data/fixtures/typo/typo_classification_impact.extended.json`
- `test-data/fixtures/typo/typo_robustness_noise.extended.json`
- `test-data/fixtures/typo/typo_on_new_word_edge_cases.extended.json`

## Status Set

`known`, `variation`, `typo_likely`, `uncertain`, `new`

## Case Shapes

### 1) Isolated typo token cases

File: `typo_tokens_by_error_type.extended.json`
Keys: `id` (string), `category` (string), `error_type` (string), `db_seed_lexemes` (string[]), `input_token` (string), `expected_status` (status enum), `expected_top_candidate` (string, empty when none expected).

### 2) Sentence context cases

File: `typo_sentences_context.extended.json`
Keys: `id`, `category`, `sentence`, `target_token`, `db_seed_lexemes`, `expected_status`, `expected_top_candidate`.

### 3) Classification impact cases

File: `typo_classification_impact.extended.json`
Keys: `id`, `category`, `db_seed_lexemes`, `surface`, `expected_status`, `expected_reason_tags` (string[]).

### 4) Robustness/noise cases

File: `typo_robustness_noise.extended.json`
Keys: `id`, `category`, `mode` (`single_token` or `note_text`), `db_seed_lexemes`.

`single_token` mode: `input_token`, `expected_status`, `expected_top_candidate`.
`note_text` mode: `input_text`, `expected_sequence` (array of `{ normalized_token, expected_status }`).

### 5) Typo-on-new-word edge cases

File: `typo_on_new_word_edge_cases.extended.json`
Keys: `id`, `category`, `db_seed_lexemes`, `surface`, `expected_status`, `expected_top_candidates` (string[], can be empty).

## Decision Config Format

Policy file: `backend/app/core/typo_policy.v1.json`

Top-level keys: `version`, `statuses`, `precedence`, `gating`, `candidate_generation`, `scoring_weights`, `decision_thresholds`, `decision_table`.

Interpretation order: exact/lemma precedence -> gating skip -> candidate confidence + margin -> fallback `new`.

Deterministic behavior; threshold tuning is config-only, no code edits.
