# Typo Benchmark Schema v1

This document defines the v1 typo fixture format and policy config format.
It follows the same conventions as existing `test-data/fixtures/lemma/*.json` packs:
flat JSON arrays of case objects with stable `id`, `category`, and explicit expected outputs.

## Fixture Files

- `test-data/fixtures/typo/typo_tokens_by_error_type.extended.json`
- `test-data/fixtures/typo/typo_sentences_context.extended.json`
- `test-data/fixtures/typo/typo_classification_impact.extended.json`
- `test-data/fixtures/typo/typo_robustness_noise.extended.json`
- `test-data/fixtures/typo/typo_on_new_word_edge_cases.extended.json`

## Status Set

- `known`
- `variation`
- `typo_likely`
- `uncertain`
- `new`

## Case Shapes

### 1) Isolated typo token cases

File: `typo_tokens_by_error_type.extended.json`

Required keys:
- `id` (string)
- `category` (string)
- `error_type` (string)
- `db_seed_lexemes` (string array)
- `input_token` (string)
- `expected_status` (status enum)
- `expected_top_candidate` (string, empty when no suggestion expected)

### 2) Sentence context cases

File: `typo_sentences_context.extended.json`

Required keys:
- `id`
- `category`
- `sentence`
- `target_token`
- `db_seed_lexemes`
- `expected_status`
- `expected_top_candidate`

### 3) Classification impact cases

File: `typo_classification_impact.extended.json`

Required keys:
- `id`
- `category`
- `db_seed_lexemes`
- `surface`
- `expected_status`
- `expected_reason_tags` (string array)

### 4) Robustness/noise cases

File: `typo_robustness_noise.extended.json`

Required keys:
- `id`
- `category`
- `mode` (`single_token` or `note_text`)
- `db_seed_lexemes`

For `single_token` mode:
- `input_token`
- `expected_status`
- `expected_top_candidate`

For `note_text` mode:
- `input_text`
- `expected_sequence` (array of `{ normalized_token, expected_status }`)

### 5) Typo-on-new-word edge cases

File: `typo_on_new_word_edge_cases.extended.json`

Required keys:
- `id`
- `category`
- `db_seed_lexemes`
- `surface`
- `expected_status`
- `expected_top_candidates` (string array, can be empty)

## Decision Config Format

Machine-readable policy file:
- `backend/app/core/typo_policy.v1.json`

Top-level keys:
- `version`
- `statuses`
- `precedence`
- `gating`
- `candidate_generation`
- `scoring_weights`
- `decision_thresholds`
- `decision_table`

Interpretation order:
1. exact/lemma precedence checks
2. gating skip checks
3. candidate confidence + margin checks
4. fallback to `new`

This gives deterministic behavior and makes threshold tuning a config change instead of a code edit.
