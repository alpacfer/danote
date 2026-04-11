# Batch Verification for Sentence Add

**Date:** 2026-04-11
**Status:** Approved

## Problem

When adding a full sentence to the sentencebank, all words are persisted to the wordbank. Each word is queued for individual verification via `verify_word_entry()` — one Gemini call per word. With 8-10 words per sentence, this saturates the Gemini rate limit and causes slow/error-prone sentence addition.

## Solution

Add `verify_word_entries_batch()` that sends all pending word verifications in a single Gemini prompt during sentence add. Results are distributed back to each word. Falls back to individual queuing on failure.

## Architecture

```
add_sentence()
  → _resolve_sentence_tokens()  [existing, unchanged]
  → _batch_verify_sentence_tokens()  [NEW]
      → collect WordVerificationInput for each new/updated token
      → runtime.verification.verify_word_entries_batch(inputs, sentence_context)
          → GeminiWordVerificationService.verify_word_entries_batch()
              → build_batch_verification_prompt()
              → _generate_content() [single Gemini call]
              → parse per-word verdicts
      → _persist_batch_verification_results() per word
```

Existing per-word verification (`queue_verification_targets`) still runs as fallback for words not covered by batch. Individual verification remains for manual word adds.

## Prompt Structure

Batch prompt contains:
1. Shared instruction block (same rules as existing single-word, condensed)
2. `sentence_context`: the full Danish sentence (shared across all entries)
3. `entries`: array of per-word verification contexts (same structure as current single-word `entry` dict, each tagged with `word_id`)

Response format:
```json
{
  "results": [
    {
      "word_id": 0,
      "verdict": "correct|incorrect",
      "word_count": 1,
      "problem": "...",
      "change_to_implement": "...",
      "suggested_actions": [...]
    },
    {"word_id": 1, "..."}
  ]
}
```

## Scope

**In scope:**
- `verify_word_entries_batch()` on `WordVerificationService` protocol + `GeminiWordVerificationService`
- `build_batch_verification_prompt()` in `verification_prompt_templates.py`
- `verify_word_entries_batch()` on `VerificationCollaborator`
- `_batch_verify_sentence_tokens()` in `sentencebank.py`
- `_persist_batch_verification_results()` for storing results per word
- Tests for batch verification service + sentencebank integration
- Updated docs

**Out of scope:**
- Batching translation/disambiguation calls (already partially batched via `translate_words_batch`)
- Frontend changes (automatic, no new UI)
- Category classification batching (separate concern)

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/verification.py` | Add `verify_word_entries_batch()` to protocol + `GeminiWordVerificationService` |
| `backend/app/services/verification_prompt_templates.py` | Add `build_batch_verification_prompt()` |
| `backend/app/services/use_cases/wordbank/collaborators/verification.py` | Add `verify_word_entries_batch()` method |
| `backend/app/services/use_cases/sentencebank.py` | Add `_batch_verify_sentence_tokens()` + call after token resolution |
| `backend/tests/use_cases/test_sentencebank_use_case.py` | Tests for batch verification integration |
| `backend/tests/services/test_verification_batch.py` | Tests for batch prompt building + parsing |

## Error Handling

- Batch call fails → fall back to queuing individual verifications (graceful degradation)
- Some words parse OK, others fail → persist successful results, queue failed ones individually
- Timeout: 30s for batch (up from 20s for individual)

## Verification Input Collection

`_batch_verify_sentence_tokens()` iterates resolved tokens after `_resolve_sentence_tokens()`. For each token that was newly persisted (not already existing), it calls `build_verification_input()` to construct the `WordVerificationInput`. Tokens that already existed in the wordbank are skipped (already verified).

## Result Distribution

Each word result from the batch response is matched back to its token by `word_id`. The collaborator persists verification records and auto-applies eligible actions (same as individual flow), then returns a summary.

## Performance Target

- N words → 1 Gemini call (down from N)
- Prompt size: ~500 tokens per word + ~200 shared instructions
- Max sentence length: ~15 words before prompt approaches token limits
