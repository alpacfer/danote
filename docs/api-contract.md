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
  - `409` when a search-seed save is attempted before `search_seed.english_translation` is fully available.
  - `400` for invalid inputs.
  - body `status` may be `inserted` or `exists`.
  - when `verification` is present, it may include `stored_surface_form`, `requested_at`, and `completed_at`.
  - `queued_verification_targets` lists each backend-queued word-page verification target using `meaning_id` plus `stored_surface_form`.
  - for search-seed saves, empty or missing `search_seed.english_translation` is rejected; the word is not persisted.

### POST `/api/wordbank/lexemes/verify`
- **Request model:** `VerifyWordRequest`.
- **Response model:** `VerifyWordResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when target lemma/surface/meaning cannot be found.
  - `400` for invalid inputs.
  - successful responses persist the verification result for the matching `(lemma, meaning_id, stored_surface_form)` target.
  - `verification` may include `stored_surface_form`, `requested_at`, and `completed_at`.
  - normal save verification checks only whether the saved lemma / meaning / selected surface placement is correct; missing paradigm members do not produce `fix_variations` suggestions in this flow.
  - `applied_categories` lists the semantic categories persisted for the reviewed root / meaning scope.
  - Gemini may reuse multiple existing categories and may mint up to 3 new broad categories when the shared catalog has no good fit.
  - category classification runs inside the same verification call and uses the full saved word scope context: reviewed gloss/translation metadata, canonical lemma metadata, selected surface metadata, sibling meaning sections, and saved surface forms for the lemma.
  - when saved COR identity resolves to a different canonical lemma than the stored lemma, that canonical lemma identity is included in Gemini's verification context so lemma-correction suggestions can target the true dictionary lemma.

### POST `/api/wordbank/lexemes/queue-verification`
- **Request model:** `QueueVerificationRequest`.
- **Response model:** `QueueVerificationResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when the target lemma / meaning / surface cannot be resolved.
  - `400` for invalid inputs.
  - successful responses return the queued verification record for the exact target.
  - request scope is `(stored_lemma, meaning_id, stored_surface_form, review_intent)`.
  - `review_intent` defaults to `general` when omitted.
  - queueing is newest-request-wins for that target scope; repeated retries/edits update the current request generation instead of creating parallel duplicate verification jobs.

### POST `/api/wordbank/lexemes/rethink-categories`
- **Request model:** `RethinkCategoriesRequest`.
- **Response model:** `RethinkCategoriesResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when the target lemma cannot be found.
  - `400` for invalid inputs.
  - body `status` can be `updated`, `skipped`, or `error`.
  - successful responses replace the persisted category set for the requested root / meaning scope without mutating verification records.
  - the rethink route reuses the same Gemini categorization flow and whole-word context payload as initial verification; it is just manually triggered.
  - `applied_categories` returns the normalized persisted category labels after the rethink run.

### POST `/api/wordbank/lexemes/complete-variations`
- **Request model:** `CompleteVariationsRequest`.
- **Response model:** `CompleteVariationsResponse`.
- **Notable status/error behavior:**
  - `503` when DB unavailable/locked.
  - `404` when the target lemma or meaning cannot be found.
  - `400` for invalid inputs.
  - body `status` can be `updated` or `skipped`.
  - v1 is meaning-scoped for noun and adjective meanings; other POS targets return `skipped`.
  - the command uses the saved meaning's `cor_lemma_idx` to resolve the paradigm and returns `skipped`
    when that stable COR identity is missing.
  - the command is also gated by verification state for that meaning:
    it returns `skipped` until the meaning target and every saved variation target in that meaning are `verified`.
  - `queued`, `error`, and `flagged` verification states return explicit user-facing skip messages explaining whether verification is still running, needs retry, or needs review resolution.
  - successful noun responses add only missing non-lemma noun variations among
    singular-definite, plural-indefinite, and plural-definite.
  - successful adjective responses add only missing non-lemma agreement forms:
    singular-indefinite `t-word`, singular-definite, and shared plural forms.
    Shared plural forms are persisted once even when they render into both plural table cells.
  - `added_surface_forms` lists the forms inserted by this call.
  - `queued_pronunciation_forms` lists the newly added forms queued for background pronunciation generation.
  - `queued_verification_targets` lists the meaning-level completion-review target(s) queued by this call so the frontend can keep polling even after leaving the lemma page.
  - the command also requeues one meaning-level verification review for the updated meaning.
    That completion review becomes the active verification source of truth for the meaning until it settles.
  - completion follow-up verification is intentionally narrow: it may only emit and later apply `fix_variations`.

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
- **Notable request/behavior details:**
  - `action.action_type` supports `fix_translation`, `fix_gloss`, `fix_variations`, `move_to_meaning_section`, and `move_to_lemma`.
  - completion-review records may expose a meaning-level `fix_variations` action that reconciles the whole saved noun or adjective variation set for that meaning in one apply request.
  - `fix_variations` is reserved for the `Complete variations` follow-up review; normal save verification does not emit that action type.
  - when the persisted verification record has `review_intent = "complete_variations"`, the backend rejects any apply attempt whose `action.action_type` is not `fix_variations`, even if the client sends it manually.
  - when Gemini provides them, `fix_variations` actions may include noun slot fields
    (`singular_indefinite_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`)
    or adjective slot fields
    (`singular_indefinite_n_word_forms`, `singular_indefinite_t_word_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`)
    so apply uses the reviewed slot sets directly instead of re-deriving them from COR.
  - `singular_indefinite_forms` may include multiple spellings for the same slot, such as `["fader", "far"]`.
  - adjective completion reviews use `n-word` / `t-word` terminology throughout; plural fields may carry the same written form in both plural slots when COR exposes one shared plural form.
  - older saved completion reviews may still carry legacy scalar slot fields (`singular_definite_form`, `plural_indefinite_form`, `plural_definite_form`); the backend still accepts them on input and can recover them from persisted review text during apply.
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
    content words drop obvious frame scaffolding but may keep short multi-word phrases when cleanup is uncertain,
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
- **Field invariants:**
  - saved search rows keep lemma translation and gloss translation separate
  - `english_translation` is only the saved lemma translation
  - `gloss_translation` is optional disambiguation context for `gloss`
  - raw `gloss` is not promoted into `english_translation`

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
  - root payload may include `categories` for non-sectioned/root meaning badges.
  - root payload may include `verification` for non-sectioned/root targets.
  - each `meaning_sections[]` item may include its own `categories`.
  - each `meaning_sections[]` item may include its own `verification`.
  - each `meaning_sections[]` item may include `gram_raw` when the backend can resolve merged COR grammar for that saved meaning scope.
  - each `surface_forms[]` item may include its own `verification` for variation-scoped Gemini results.
  - each `surface_forms[]` item may include `gram_raw` when the backend can resolve COR grammar for that saved form.
  - for sectioned lemmas, top-level `surface_forms[]` may include the saved lemma form itself
    so the client can bind exact-lemma pronunciation and metadata.
  - sectioned meaning `surface_forms[]` exclude rows whose normalized form matches the lemma;
    those lemma-form rows stay available only through top-level `surface_forms[]` when stored.
  - noun `surface_forms[]` are ordered with non-slot/irregular forms first, then singular-definite, plural-indefinite, and plural-definite.
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
      "categories": ["Actions", "School"],
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
          "gram_raw": "vb. præs. akt",
          "has_pronunciation": false,
          "verification": {
            "status": "queued",
            "provider": "gemini",
            "reviewer_role": "Professional Danish Language Expert",
            "message": "Word verification queued.",
            "composed_word_count": null,
            "stored_surface_form": "lærer",
            "requested_at": "2026-03-13T12:00:00+00:00",
            "suggested_actions": []
          }
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
          "gram_raw": "sb. fk. sg. best",
          "categories": ["Household Objects"],
          "verification": {
            "status": "verified",
            "provider": "gemini",
            "reviewer_role": "Professional Danish Language Expert",
            "message": "Verification passed.",
            "composed_word_count": null,
            "stored_surface_form": null,
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
              "has_pronunciation": false,
              "verification": {
                "status": "flagged",
                "provider": "gemini",
                "reviewer_role": "Professional Danish Language Expert",
                "message": "Review needed.",
                "composed_word_count": 1,
                "stored_surface_form": "bogen",
                "requested_at": "2026-03-13T12:00:00+00:00",
                "completed_at": "2026-03-13T12:00:04+00:00",
                "problem": "Saved variation translation does not match this meaning.",
                "change_to_implement": "Move the variation to another meaning section.",
                "suggested_actions": [
                  {
                    "action_type": "move_to_meaning_section",
                    "target_meaning_id": 2
                  }
                ]
              }
            }
          ]
        }
      ],
      "surface_forms": [
        {
          "form": "bog",
          "pos_tag": "NOUN",
          "morphology": "Gender=Com|Number=Sing|Definite=Def",
          "gram_raw": "sb. fk. sg. best",
          "has_pronunciation": false
        }
      ]
    }
    ```
  - **Completion-review example** (`is_sectioned: true`, meaning-level fix action):
    ```json
    {
      "lemma": "mor",
      "english_translation": null,
      "pos_tag": null,
      "morphology": null,
      "is_sectioned": true,
      "meaning_sections": [
        {
          "id": 1,
          "meaning_key": "person",
          "gloss": "person",
          "english_translation": "mother",
          "pos_tag": "NOUN",
          "morphology": "Gender=Com|Number=Sing|Definite=Ind",
          "verification": {
            "status": "flagged",
            "provider": "gemini",
            "reviewer_role": "Professional Danish Language Expert",
            "message": "Review needed.",
            "composed_word_count": 1,
            "stored_surface_form": null,
            "requested_at": "2026-03-15T10:55:00+00:00",
            "completed_at": "2026-03-15T10:57:00+00:00",
            "problem": "The plural surface forms provided for the noun 'mor' are incorrect.",
            "change_to_implement": "Replace the completed variation set with the correct plural forms.",
            "suggested_actions": [
              {
                "action_type": "fix_variations",
                "reason": "Replace the saved variation set with the reviewed noun forms for this meaning.",
                "singular_indefinite_forms": ["mor"],
                "singular_definite_forms": ["moren"],
                "plural_indefinite_forms": ["mødre"],
                "plural_definite_forms": ["mødrene"]
              }
            ]
          },
          "surface_forms": [
            {
              "form": "morer",
              "pos_tag": "NOUN",
              "morphology": "Gender=Com|Number=Plur|Definite=Ind",
              "lemma": "mor",
              "lemma_translation": "mother",
              "gloss": "person",
              "has_pronunciation": false
            },
            {
              "form": "morerne",
              "pos_tag": "NOUN",
              "morphology": "Gender=Com|Number=Plur|Definite=Def",
              "lemma": "mor",
              "lemma_translation": "mother",
              "gloss": "person",
              "has_pronunciation": false
            }
          ]
        }
      ],
      "surface_forms": [
        {
          "form": "mor",
          "pos_tag": "NOUN",
          "morphology": "Gender=Com|Number=Sing|Definite=Ind",
          "has_pronunciation": false
        }
      ]
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
