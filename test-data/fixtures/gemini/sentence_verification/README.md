# Gemini Sentence Verification Fixtures

This directory stores replay fixtures for raw Gemini sentence-verification responses.

Use these when a real provider response needs to be pinned and replayed in pytest.

## Fixture Schema

Each `*.json` file should look like this:

```json
{
  "source_text": "jeg har en stor",
  "raw_response": "{\"is_valid\":false,\"errors\":[{\"start\":0,\"end\":15,\"message\":\"Incomplete sentence fragment.\"}],\"corrected_text\":null,\"language\":\"da\"}",
  "expected": {
    "is_valid": true,
    "errors": [],
    "corrected_text": null,
    "language": "da"
  },
  "recording": {
    "recorded_at_utc": "2026-04-18T12:00:00+00:00",
    "model": "gemini-3.1-flash-lite-preview",
    "prompt": "..."
  }
}
```

The replay test reads `source_text`, feeds `raw_response` back through `GeminiSentenceVerificationService.verify_sentence`, and asserts the normalized result matches `expected`.

## Record a Fixture

From the repo root:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/record-sentence-verification-fixture.py \
  --fixture-name partial-input-no-autocomplete \
  --source-text "jeg har en stor"
```

This writes a fixture file in this directory using the current Gemini settings.

The recorder seeds `expected` from the parser's current output. If the raw Gemini message reveals a bug, edit the `expected` block to the behavior you want before running the replay test.

## Run Replay Tests

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_sentence_verification_gemini_replay.py
```
