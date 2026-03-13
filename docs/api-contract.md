# API Contract

This document enumerates all HTTP routes currently declared under `backend/app/api/routes/*.py`.

## Contract source

Route decorators are the source of truth in `backend/app/api/routes/`, and API DTOs live in `backend/app/api/schemas/v1/`. Some token endpoints currently use request/response models declared inline in `backend/app/api/routes/tokens.py` (not yet in `schemas/v1`).

## Root

### GET `/api/`
- **Request model:** none.
- **Response model:** inline `dict[str, str]` (`{"status": "ok", "message": "danote backend scaffold"}`).
- **Notable status/error behavior:** normal success `200`.

### GET `/api/health`
- **Request model:** none.
- **Response model:** `HealthResponse` (`backend/app/api/schemas/v1/root.py`).
- **Notable status/error behavior:** returns `200` with `status: "ok"` or `"degraded"` depending on DB/NLP/service readiness.

## Analyze

### POST `/api/analyze`
- **Request model:** `AnalyzeRequest`.
- **Response model:** `AnalyzeResponse`.
- **Notable status/error behavior:**
  - `503` when NLP is unavailable (`require_nlp_ready`).
  - `503` when DB is unavailable/locked.
  - `400` when the use case raises validation/value errors.

### POST `/api/analyze/enrich-token`
- **Request model:** `EnrichTokenRequest`.
- **Response model:** `ResolveQueryResponse`.
- **Notable status/error behavior:**
  - `503` when DB is unavailable/locked.
  - `400` for value errors from query resolution.

## Tokens

### POST `/api/tokens/feedback`
- **Request model:** inline `TokenFeedbackRequest` (`backend/app/api/routes/tokens.py`).
- **Response model:** inline `TokenFeedbackResponse`.
- **Notable status/error behavior:**
  - `503` when typo engine is unavailable.
  - `503` when typo DB operations fail (`sqlite3.OperationalError`).

### POST `/api/tokens/ignore`
- **Request model:** inline `TokenIgnoreRequest` (`backend/app/api/routes/tokens.py`).
- **Response model:** inline `TokenIgnoreResponse`.
- **Notable status/error behavior:**
  - `503` when typo engine is unavailable.
  - `503` when typo DB operations fail (`sqlite3.OperationalError`).

## Developer

### POST `/api/developer/api-keys`
- **Request model:** `DeveloperApiKeysUpdateRequest`.
- **Response model:** `DeveloperApiKeysUpdateResponse`.
- **Notable status/error behavior:** updates runtime API key overrides and service wiring; returns configured-provider flags in `configured`.

### POST `/api/developer/gemini-probe`
- **Request model:** none.
- **Response model:** `GeminiProbeResponse`.
- **Notable status/error behavior:** endpoint returns probe payload with `status` (`ok`/`error`) and diagnostic message; probe failures are represented in-body (typically `200` response).

### POST `/api/developer/translation-probe`
- **Request model:** none.
- **Response model:** `DeveloperServiceProbeResponse`.
- **Notable status/error behavior:** endpoint returns probe payload with `status` (`ok`/`error`) and provider diagnostics; failures are represented in-body.

### POST `/api/developer/tts-probe`
- **Request model:** none.
- **Response model:** `DeveloperServiceProbeResponse`.
- **Notable status/error behavior:** endpoint returns probe payload with `status` (`ok`/`error`) and message; failures are represented in-body.

## Sentencebank

### POST `/api/sentencebank/sentences`
- **Request model:** `AddSentenceRequest`.
- **Response model:** `AddSentenceResponse`.
- **Notable status/error behavior:**
  - `503` when DB is unavailable/locked.
  - `400` for value errors.
  - `status` in body is `inserted` or `exists`.

### GET `/api/sentencebank/sentences`
- **Request model:** none.
- **Response model:** `SentenceListResponse`.
- **Notable status/error behavior:**
  - `503` when DB is unavailable/locked.

## Wordbank

### POST `/api/wordbank/lexemes`
- **Request model:** `AddWordRequest`.
- **Response model:** `AddWordResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `503` for runtime DB compatibility errors (e.g., reset-required conditions).
  - `400` for invalid inputs.
  - body `status` may be `inserted` or `exists`.
  - when `verification` is present, it may include `stored_surface_form`, `requested_at`, and `completed_at`.

### POST `/api/wordbank/lexemes/verify`
- **Request model:** `VerifyWordRequest`.
- **Response model:** `VerifyWordResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when target lemma/surface/meaning cannot be found.
  - `400` for invalid inputs.
  - successful responses persist the verification result for the matching lemma/meaning target.
  - `verification` may include `stored_surface_form`, `requested_at`, and `completed_at`.

### POST `/api/wordbank/lexemes/pronunciation`
- **Request model:** `GeneratePronunciationRequest`.
- **Response model:** `GeneratePronunciationResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when the target entry is not found.
  - body `status` can be `generated`, `unavailable`, or `skipped`.

### POST `/api/wordbank/lexemes/apply-verification-changes`
- **Request model:** `ApplyVerificationChangesRequest`.
- **Response model:** `ApplyVerificationChangesResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when source/target meaning context cannot be resolved.
  - body `status` can be `applied` or `skipped`.

### POST `/api/wordbank/translation`
- **Request model:** `GenerateTranslationRequest`.
- **Response model:** `GenerateTranslationResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - body `status` can be `generated` or `unavailable`.
  - Single-word translations are normalized after provider lookup:
    content words are returned as headword-first English output when cleanup is confident,
    while function words may retain only short lexicalized context such as `because of`.

### POST `/api/wordbank/reverse-translation`
- **Request model:** `GenerateReverseTranslationRequest`.
- **Response model:** `GenerateReverseTranslationResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - body `status` can be `generated` or `unavailable`.

### POST `/api/wordbank/detect-language`
- **Request model:** `DetectWordLanguageRequest`.
- **Response model:** `DetectWordLanguageResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.

### POST `/api/wordbank/resolve-query`
- **Request model:** `ResolveQueryRequest`.
- **Response model:** `ResolveQueryResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `400` for invalid resolver inputs.

### POST `/api/wordbank/phrase-translation`
- **Request model:** `GeneratePhraseTranslationRequest`.
- **Response model:** `GeneratePhraseTranslationResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - body `status` can be `generated`, `cached`, or `unavailable`.

### GET `/api/wordbank/lemmas`
- **Request model:** none.
- **Response model:** `LemmaListResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### GET `/api/wordbank/search`
- **Request model:** none (`query` and `limit` query parameters).
- **Response model:** `WordbankSearchResponse`.
- **Notable status/error behavior:**
  - query validation failures return `422` (e.g., empty query or limit out of range).
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### GET `/api/wordbank/search/cor-form`
- **Request model:** none (`form`, `limit`, `include_translations` query parameters).
- **Response model:** `CORSearchFormResponse`.
- **Notable status/error behavior:**
  - query validation failures return `422`.
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### GET `/api/wordbank/search/cor-lemma/{lemma_idx}`
- **Request model:** none (`lemma_idx` path param, optional `limit` query parameter).
- **Response model:** `CORLemmaParadigmResponse`.
- **Notable status/error behavior:**
  - path/query validation failures return `422`.
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### GET `/api/wordbank/lemmas/{lemma}`
- **Request model:** none (`lemma` path parameter).
- **Response model:** `LemmaDetailsResponse`.
- **Notable response behavior:**
  - root payload may include `verification` for non-sectioned/root targets.
  - each `meaning_sections[]` item may include its own `verification`.
  - verification objects use the same additive fields as add/verify responses:
    `stored_surface_form`, `requested_at`, `completed_at`, and `suggested_actions`.
- **Canonical response examples:**
  - **Non-sectioned** (`is_sectioned: false`):
    ```json
    {
      "lemma": "lære",
      "english_translation": null,
      "pos_tag": "VERB",
      "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
      "is_sectioned": false,
      "verification": {
        "status": "queued",
        "provider": "gemini",
        "reviewer_role": "Professional Danish Language Expert",
        "message": "Word verification queued.",
        "composed_word_count": null,
        "stored_surface_form": "lærer",
        "requested_at": "2026-03-13T12:00:00+00:00",
        "suggested_actions": []
      },
      "meaning_sections": [],
      "surface_forms": [
        {
          "form": "lærer",
          "pos_tag": "VERB",
          "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
          "has_pronunciation": false
        }
      ]
    }
    ```
  - **Sectioned** (`is_sectioned: true`):
    ```json
    {
      "lemma": "bog",
      "english_translation": null,
      "pos_tag": null,
      "morphology": null,
      "is_sectioned": true,
      "meaning_sections": [
        {
          "id": 1,
          "meaning_key": "book",
          "gloss": "book",
          "english_translation": "book",
          "gloss_translation": "book",
          "pos_tag": "NOUN",
          "morphology": "Gender=Com|Number=Sing|Definite=Def",
          "verification": {
            "status": "verified",
            "provider": "gemini",
            "reviewer_role": "Professional Danish Language Expert",
            "message": "Verification passed.",
            "composed_word_count": null,
            "stored_surface_form": "bogen",
            "requested_at": "2026-03-13T12:00:00+00:00",
            "completed_at": "2026-03-13T12:00:03+00:00",
            "suggested_actions": []
          },
          "surface_forms": [
            {
              "form": "bogen",
              "pos_tag": "NOUN",
              "morphology": "Gender=Com|Number=Sing|Definite=Def",
              "lemma": "bog",
              "lemma_translation": "book",
              "gloss": "book",
              "gloss_translation": "book",
              "gram_raw": "sb. fk. sg. best",
              "has_pronunciation": false
            }
          ]
        }
      ],
      "surface_forms": []
    }
    ```
- **Notable status/error behavior:**
  - `404` when lemma is not found.
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### GET `/api/wordbank/pronunciation`
- **Request model:** none (`form` query parameter).
- **Response model:** raw audio bytes (`fastapi.Response`, dynamic `media_type`), not a Pydantic schema.
- **Notable status/error behavior:**
  - query validation failures return `422`.
  - `404` when pronunciation is not found.
  - `503` when DB unavailable/locked.
  - `503` for runtime errors surfaced by use case.

### DELETE `/api/wordbank/database`
- **Request model:** none.
- **Response model:** `ResetDatabaseResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `503` with `Database reset failed: ...` for filesystem/OS reset failures.
