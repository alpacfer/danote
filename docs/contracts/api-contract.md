# API Contract

All HTTP routes in `backend/app/api/routes/*.py`.

## Contract source

Routes: `backend/app/api/routes/`. DTOs: `backend/app/api/schemas/v1/`. Some token endpoints use inline models in `backend/app/api/routes/tokens.py`.

## Root

### GET `/api/`
- **Request model:** none.
- **Response model:** inline `dict[str, str]` (`{"status": "ok", "message": "danote backend scaffold"}`).
- **Notable status/error behavior:** `200`.

### GET `/api/health`
- **Request model:** none.
- **Response model:** `HealthResponse` (`backend/app/api/schemas/v1/root.py`).
- **Notable status/error behavior:** `200` with `status: "ok"` or `"degraded"` per DB/NLP readiness.

## Analyze

### POST `/api/analyze`
- **Request model:** `AnalyzeRequest`.
- **Response model:** `AnalyzeResponse`.
- **Notable status/error behavior:** `503` NLP unavailable. `503` DB unavailable/locked. `400` validation/value errors.

### POST `/api/analyze/enrich-token`
- **Request model:** `EnrichTokenRequest`.
- **Response model:** `ResolveQueryResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `400` value errors from query resolution.

## Tokens

### POST `/api/tokens/feedback`
- **Request model:** inline `TokenFeedbackRequest` (`backend/app/api/routes/tokens.py`).
- **Response model:** inline `TokenFeedbackResponse`.
- **Notable status/error behavior:** `503` typo engine unavailable. `503` typo DB ops fail (`sqlite3.OperationalError`).

### POST `/api/tokens/ignore`
- **Request model:** inline `TokenIgnoreRequest` (`backend/app/api/routes/tokens.py`).
- **Response model:** inline `TokenIgnoreResponse`.
- **Notable status/error behavior:** `503` typo engine unavailable. `503` typo DB ops fail (`sqlite3.OperationalError`).

## Developer

### POST `/api/developer/api-keys`
- **Request model:** `DeveloperApiKeysUpdateRequest`.
- **Response model:** `DeveloperApiKeysUpdateResponse`.
- **Notable status/error behavior:** updates runtime API key overrides + service wiring; returns `configured` provider flags.

### POST `/api/developer/gemini-probe`
- **Request model:** none.
- **Response model:** `GeminiProbeResponse`.
- **Notable status/error behavior:** returns probe payload with `status` (`ok`/`error`) + diagnostics; failures in-body (typically `200`).

### POST `/api/developer/translation-probe`
- **Request model:** none.
- **Response model:** `DeveloperServiceProbeResponse`.
- **Notable status/error behavior:** returns probe payload with `status` (`ok`/`error`) + provider diagnostics; failures in-body.

### POST `/api/developer/tts-probe`
- **Request model:** none.
- **Response model:** `DeveloperServiceProbeResponse`.
- **Notable status/error behavior:** returns probe payload with `status` (`ok`/`error`) + message; failures in-body.

## Sentencebank

### POST `/api/sentencebank/sentences`
- **Request model:** `AddSentenceRequest`.
- **Response model:** `AddSentenceResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `400` value errors. body `status`: `inserted` or `exists`.
- **Field invariants:** response now includes hydrated sentence details (`id`, `created_at`, `tokens[]`, `has_pronunciation`). `tokens[]` carries `token_index`, `surface_form`, `stored_lemma`, `lexeme_id`, nullable `meaning_id`, POS/morphology, optional gloss, and translation fields. Insert responses may also include `pronunciation` with `status: queued|skipped` plus `sentence_id` when background sentence audio generation is considered.

### GET `/api/sentencebank/sentences`
- **Request model:** none.
- **Response model:** `SentenceListResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked.
- **Field invariants:** each item includes nested `tokens[]` using the same sentence-token card contract as `POST`, plus `has_pronunciation` derived from persisted sentence audio.

### POST `/api/sentencebank/sentences/pronunciation`
- **Request model:** `GenerateSentencePronunciationRequest` (`sentence_id`, `force: bool = False`).
- **Response model:** `GenerateSentencePronunciationResponse` (`status: generated|unavailable|skipped`, `sentence_id`, `source_text`).
- **Notable status/error behavior:** `404` sentence not found. `503` DB unavailable/locked.

### GET `/api/sentencebank/pronunciation`
- **Request model:** none (`sentence_id` query param).
- **Response model:** raw audio bytes (`fastapi.Response`, dynamic `media_type`), not Pydantic schema.
- **Notable status/error behavior:** `422` validation failures. `404` sentence or pronunciation not found. `503` DB unavailable/locked. `503` runtime errors when TTS is unavailable and no stored sentence audio exists.

### POST `/api/sentencebank/verify-sentence`
- **Request model:** `VerifySentenceRequest` (`source_text: str`, max 100 chars).
- **Response model:** `VerifySentenceResponse` (`is_valid`, `errors: [{start, end, message}]`, `corrected_text`, `language`).
- **Notable status/error behavior:** `422` empty or >100 char text. `503` DB unavailable. No Gemini service → returns `is_valid=true`.

### POST `/api/sentencebank/search-preview`
- **Request model:** `SentenceSearchPreviewRequest` (`source_text: str`, max 100 chars, `fast: bool = False`).
- **Response model:** `SentenceSearchPreviewResponse` (`status: "ready" | "blocked" | "preview"`, `query_language`, `source_text`, `english_translation`, `is_valid`, `errors`, `message`).
- **Notable status/error behavior:** `422` empty or >100 char text. `503` DB unavailable.
- **Field invariants:**
  - `source_text`: finalized Danish sentence candidate for sidebar display and save. `null` only when preview is blocked.
  - `query_language`: detected language of the original query, not the finalized Danish sentence.
  - `english_translation`: for Danish/unknown queries, derived from the finalized Danish `source_text`; for English-origin queries, the corrected original English sentence used for translation, not a Danish-to-English retranslation.
  - `status = "preview"`: fast preview path. Skips sentence verification, uses heuristic language detection plus the configured translation service, and is intended for immediate sidebar feedback while the full result is still pending.
  - `status = "ready"`: save may proceed when `source_text` is non-null.
  - `status = "blocked"`: sidebar disables save and surfaces `message`.
  - Explicit English queries translate the corrected or normalized English sentence into Danish and do not perform a second Danish verification pass. Unknown-language queries do not auto-switch into English flow.

## Wordbank

### POST `/api/wordbank/lexemes`
- **Request model:** `AddWordRequest`.
- **Response model:** `AddWordResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `503` runtime DB compatibility errors (e.g. reset-required). `400` invalid inputs. body `status`: `inserted` or `exists`.
- **Field invariants:**
  - `verification` may include `stored_surface_form`, `requested_at`, `completed_at`.
  - `queued_pronunciation_forms`: normalized lemma/surface forms queued for background pronunciation. Add/save flows use shared backend queue, not browser-side requests.
  - `saved_snapshot.related_words`: lemma-scoped enrichment with `status` (`queued|ready|empty|error`), optional `message`, `items[]` for compound-component related words. Returns `status = "queued"` immediately after enqueue.
  - Word-page payloads include `additional_translations` on root and each meaning section: alternate English translations for that saved scope.
  - `queued_verification_targets`: backend-queued targets using `meaning_id` + `stored_surface_form`.
  - Search-seed saves: empty/missing `search_seed.english_translation` allowed; persisted with blank translation.
  - Low-confidence glossless verb seeds whose translation collapses to lemma (e.g. `to bile` for `bile`): backend drops translation, saves with blank `english_translation`.

### POST `/api/wordbank/lexemes/verify`
- **Request model:** `VerifyWordRequest`.
- **Response model:** `VerifyWordResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. `400` invalid inputs.
- **Field invariants:**
  - Success persists verification for matching `(lemma, meaning_id, stored_surface_form)`.
  - `verification` may include `stored_surface_form`, `requested_at`, `completed_at`.
  - `verification.message`: short status-like (`OK`, `Review needed`, `Verification failed`, `Queued`).
  - `verification.problem`: one short mismatch sentence. `verification.change_to_implement`: one short imperative.
  - Normal save verification: checks saved lemma/meaning/surface placement correctness only; missing paradigm members do NOT produce `fix_variations`.
  - Action availability by target scope: lemma/meaning targets may emit `fix_translation` or `move_to_lemma`; surface-form targets emit only relocation (`move_to_meaning_section`, `move_to_lemma`), never translation fixes.
  - Surface-form reviews producing only translation-fix output: treated as irrelevant, persisted as `verified` not `flagged`.
  - Gemini verification context includes saved POS/morphology + COR `gram_raw` + paradigm-slot evidence. Relocation suggestions contradicting paradigm evidence are discarded.
  - Meaning-level review attempting lemma move when paradigm evidence still matches current lemma + translated gloss hint exists: backend backfills `fix_translation` from hint instead of contradictory move.
  - Meaning/lemma review with missing/low-confidence translation + translated gloss hint: backend persists `fix_translation` from hint even when Gemini returns `correct`.
  - COR/translated glosses used as sense-disambiguation context only; persisted review prose restricted to translation/placement feedback. Backend suppresses gloss-only critique; rewrites translation-fix copy so user never sees gloss-change suggestions.
  - `verification.suggested_actions`: sole apply contract. Backend apply does NOT recover actions from prose.
  - `applied_categories`: semantic categories persisted for reviewed root/meaning scope.
  - After verification persistence for `verified`/`flagged`, category classification runs as separate follow-up. Prefers existing categories; mints at most 1 new broad category.
  - When saved COR identity resolves to different canonical lemma, that canonical identity included in Gemini context for lemma-correction targeting.

### POST `/api/wordbank/lexemes/queue-verification`
- **Request model:** `QueueVerificationRequest`.
- **Response model:** `QueueVerificationResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. `400` invalid inputs.
- **Field invariants:**
  - Request scope: `(stored_lemma, meaning_id, stored_surface_form, review_intent)`. `review_intent` defaults to `general`.
  - Newest-request-wins for that scope; retries/edits update current generation instead of creating duplicates.

### POST `/api/wordbank/lexemes/rethink-categories`
- **Request model:** `RethinkCategoriesRequest`.
- **Response model:** `RethinkCategoriesResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. `400` invalid inputs. body `status`: `updated`, `skipped`, or `error`.
- **Field invariants:**
  - Replaces persisted category set for requested root/meaning scope without mutating verification records.
  - Runs standalone category-classification Gemini flow. Prefers existing labels; mints at most 1 new broad category.
  - `applied_categories`: normalized persisted labels after rethink.

### POST `/api/wordbank/lexemes/find-alternative-translations`
- **Request model:** `FindAlternativeTranslationsRequest`.
- **Response model:** `FindAlternativeTranslationsResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. `400` invalid inputs. body `status`: `updated`, `skipped`, or `error`.
- **Field invariants:**
  - Lemma/meaning scoped only; not surface-form rows.
  - Backend sends saved lemma, scope POS/morphology, gloss, primary translation, existing `additional_translations` to Gemini.
  - Gemini constrained to very common English alternatives for that exact saved sense; may return empty list.
  - When Gemini proposes better primary: backend replaces persisted `english_translation`. Distinct alternates inserted into `additional_translations`.
  - `primary_translation`: final persisted primary after update. `added_additional_translations`: only new alternates from this request.

### POST `/api/wordbank/lexemes/complete-variations`
- **Request model:** `CompleteVariationsRequest`.
- **Response model:** `CompleteVariationsResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. `400` invalid inputs. body `status`: `updated` or `skipped`.
- **Field invariants:**
  - v1 is meaning-scoped for noun, adjective, verb meanings; other POS returns `skipped`.
  - Uses saved meaning's `cor_lemma_idx` to resolve paradigm; returns `skipped` when missing.
  - Gated by verification state: returns `skipped` until meaning target + all saved variations are `verified`. `queued`/`error`/`flagged` states return explicit skip messages.
  - Noun: adds missing non-lemma variations among singular-definite, plural-indefinite, plural-definite.
  - Adjective: adds missing agreement forms: singular-indefinite `t-word`, singular-definite, shared plurals. Shared plural persisted once.
  - Verb: adds missing forms: present, past, imperative, past participle. Infinitive row is lemma/default, not duplicated.
  - `added_surface_forms`: forms inserted. `queued_pronunciation_forms`: forms queued for background pronunciation (lemma-scoped, merged by `stored_lemma`; may include lemma itself).
  - `queued_verification_targets`: meaning-level completion-review targets for polling.
  - Requeues one meaning-level verification review; becomes active source of truth until settled. Completion review is narrow: may only emit/apply `fix_variations`.

### POST `/api/wordbank/lexemes/pronunciation`
- **Request model:** `GeneratePronunciationRequest`.
- **Response model:** `GeneratePronunciationResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` target not found. body `status`: `generated`, `unavailable`, or `skipped`.

### POST `/api/wordbank/lexemes/apply-verification-changes`
- **Request model:** `ApplyVerificationChangesRequest`.
- **Response model:** `ApplyVerificationChangesResponse`.
- **Notable request/behavior details:**
  - `action.action_type`: `fix_translation`, `fix_variations`, `move_to_meaning_section`, `move_to_lemma`.
  - `fix_translation`: valid only for lemma/meaning-scoped targets with `stored_surface_form = null`; rejected for surface-scoped.
  - Completion-review records expose meaning-level `fix_variations` reconciling whole variation set. `fix_variations` reserved for completion follow-up; normal save verification never emits it.
  - When persisted `review_intent = "complete_variations"`: backend rejects any apply whose `action_type != fix_variations`.
  - `fix_variations` slot fields (provided by Gemini, used directly, not re-derived from COR):
    - Noun: `singular_indefinite_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`
    - Adjective: `singular_indefinite_n_word_forms`, `singular_indefinite_t_word_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`
    - Verb: `infinitive_forms`, `present_forms`, `past_forms`, `imperative_forms`, `past_participle_forms`
  - `singular_indefinite_forms` may include multiple spellings (e.g. `["fader", "far"]`).
  - Adjective: uses `n-word`/`t-word` terminology; plural fields may carry same form in both slots for shared plurals.
  - Verb: fixed row labels `Infinitive`, `Present`, `Past`, `Imperative`, `Past participle`.
  - `fix_variations` must be fully structured. Apply does NOT recover slots from `problem`/`change_to_implement`.
  - Persisted Gemini `fix_translation` and `fix_variations` applies are also written to the per-lemma verification change log for later inspection/revert.
- **Notable status/error behavior:** `503` DB unavailable/locked. `404` source/target context not found. body `status`: `applied` or `skipped`.

### GET `/api/wordbank/lexemes/verification-changes`
- **Request model:** none (`stored_lemma` query param).
- **Response model:** `GetVerificationChangesResponse`.
- **Notable request/behavior details:**
  - Returns newest-first per-lemma verification history entries.
  - Entries currently cover persisted Gemini `fix_translation` and `fix_variations` applies.
  - Each item includes `before_json`, `after_json`, `applied_at`, optional `reverted_at`, and `provider`.
- **Notable status/error behavior:** `400` invalid `stored_lemma`. `503` DB unavailable/locked.

### POST `/api/wordbank/lexemes/revert-verification-change`
- **Request model:** `RevertVerificationChangeRequest`.
- **Response model:** `RevertVerificationChangeResponse`.
- **Notable request/behavior details:**
  - Reverts a per-lemma change-log entry by restoring the stored `before_json` snapshot directly in the DB.
  - Supported revert targets: `fix_translation`, `fix_variations`.
  - Rejects missing `stored_lemma`; mismatched or unknown change ids return body `status = "not_found"`.
  - Already reverted entries return body `status = "already_reverted"`.
- **Notable status/error behavior:** `400` invalid request body. `503` DB unavailable/locked.

### POST `/api/wordbank/translation`
- **Request model:** `GenerateTranslationRequest`.
- **Response model:** `GenerateTranslationResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. body `status`: `generated` or `unavailable`.
- Single-word translations normalized after provider lookup: content words drop frame scaffolding but may keep short multi-word phrases; function words may retain short lexicalized context (e.g. `because of`).

### POST `/api/wordbank/reverse-translation`
- **Request model:** `GenerateReverseTranslationRequest`.
- **Response model:** `GenerateReverseTranslationResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. body `status`: `generated` or `unavailable`.

### POST `/api/wordbank/detect-language`
- **Request model:** `DetectWordLanguageRequest`.
- **Response model:** `DetectWordLanguageResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked.

### POST `/api/wordbank/resolve-query`
- **Request model:** `ResolveQueryRequest`.
- **Response model:** `ResolveQueryResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `400` invalid resolver inputs.
- **Field invariants:**
  - COR-backed Danish add-option labels suppress provider self-translations (no literal Danish lemma echoes).
  - DeepL/Azure search labels use same fallback via shared primary-provider contract.
  - Gemini contextual translation takes precedence over self-translated primary-provider labels, including same-text lemma echoes for valid cognates/loanwords.
  - Primary self-translates + Gemini has no better translation: add-option labels may fall back to translated COR gloss.
  - Primary self-translates + Gemini returns nothing + no translated gloss: label falls back to query surface.

### POST `/api/wordbank/phrase-translation`
- **Request model:** `GeneratePhraseTranslationRequest`.
- **Response model:** `GeneratePhraseTranslationResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. body `status`: `generated`, `cached`, or `unavailable`.

### GET `/api/wordbank/lemmas`
- **Request model:** none.
- **Response model:** `LemmaListResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `503` runtime errors.

### GET `/api/wordbank/search`
- **Request model:** none (`query`, `limit` query params).
- **Response model:** `WordbankSearchResponse`.
- **Notable status/error behavior:** `422` validation failures (empty query, limit out of range). `503` DB unavailable/locked. `503` runtime errors.
- **Field invariants:** saved search rows keep lemma translation + gloss translation separate. `english_translation` = saved lemma translation only. `gloss_translation` = optional disambiguation context. Raw `gloss` not promoted into `english_translation`. `did_you_mean`: non-null when query had no direct matches and a Levenshtein-close wordbank lemma was found; `items` then contains results for the corrected word.

### GET `/api/wordbank/search/cor-form`
- **Request model:** none (`form`, `limit`, `include_translations` query params).
- **Response model:** `CORSearchFormResponse`.
- **Notable status/error behavior:** `422` validation failures. `503` DB unavailable/locked. `503` runtime errors.
- **Field invariants:**
  - `lemma_translation` + `gloss_translation` separate; gloss text never promoted into `lemma_translation`.
  - `saveable_translation`: backend-authoritative search save value. Equals `lemma_translation` when usable; may carry gloss-derived fallback when `lemma_translation` is `null`.
  - `lemma_translation_provider`: which provider supplied displayed lemma translation.
  - `lemma_translation_status`: `provider`, `gemini`, `gloss_fallback`, or `missing`.
  - `lemma_translation_reason`: final decision reason (`provider_ok`, `provider_self_translation`, `gemini_ok`, `gemini_missing`, `gemini_self_translation`, `gloss_fallback_used`).
  - DeepL/Azure COR search: same fallback via shared primary-provider contract.
  - Primary framed translation collapses to Danish lemma/form (e.g. `at bile -> to bile`): treated as invalid, prefers Gemini contextual translation.
  - Gloss not required for Gemini fallback; glossless entries send Danish lemma + POS/morphology; verbs framed as infinitives (e.g. `at bile`).
  - Gemini returns non-empty translation: trusted even if English matches Danish lemma exactly.
  - Gemini returns nothing: backend may keep `lemma_translation = null` with gloss-derived `saveable_translation`; no gloss fallback means both stay `null`.
  - `did_you_mean`: non-null when `form` had no COR entries and a Levenshtein-close COR lemma was found; `groups` then contains results for the corrected lemma.

### GET `/api/wordbank/search/cor-lemma/{lemma_idx}`
- **Request model:** none (`lemma_idx` path param, optional `limit` query param).
- **Response model:** `CORLemmaParadigmResponse`.
- **Notable status/error behavior:** `422` path/query validation failures. `503` DB unavailable/locked. `503` runtime errors.

### GET `/api/wordbank/lemmas/{lemma}`
- **Request model:** none (`lemma` path param).
- **Response model:** `LemmaDetailsResponse`.
- **Notable response behavior:**
  - Root payload may include `categories`, `verification`, `additional_translations: string[]`.
  - Each `meaning_sections[]` may include `categories`, `verification`, `gram_raw`, `additional_translations: string[]`.
  - Each `surface_forms[]` may include `verification`, `gram_raw`.
  - Sectioned lemmas: top-level `surface_forms[]` may include saved lemma form for pronunciation/metadata binding. Sectioned meaning `surface_forms[]` exclude lemma-matching rows (available via top-level only).
  - Noun `surface_forms[]` ordered: non-slot/irregular first, then singular-definite, plural-indefinite, plural-definite.
  - Verification objects use same additive fields as add/verify responses.
  - Root `related_words`: `status` = `queued` (running) | `ready` (has `items[]`) | `empty` (no components survive filtering) | `error` (job failed).
  - Root `linked_sentences[]`: lemma-level reverse sentence links with `id`, `source_text`, `english_translation`, `created_at`, `matched_token_indexes[]`, and nested sentence `tokens[]`.
  - Each `related_words.items[]` row:
    - `relation_type`: `compound_component | compound_host`
    - Gemini-provided `lemma`, `english_translation`, `pos_tag`
    - Verb translations normalized to infinitive English (`to <verb>`)
    - `compound_host`: reverse links from other saved compounds including this lemma
    - `saved_match.status`: `unsaved | saved_lemma | saved_variation`
    - `saved_match.target_lemma` / `target_meaning_id` for eye/open actions
    - `display_variant` when COR resolves to one saveable match
    - `candidate_variants[]` when multiple same-POS COR matches remain (client must let user choose)
  - Related-word enrichment resolving a saved target with new translation: translation added to `additional_translations` for that scope automatically.
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
        "message": "Queued",
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
            "message": "Queued",
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
- **Notable status/error behavior:** `404` lemma not found. `503` DB unavailable/locked. `503` runtime errors.

### GET `/api/wordbank/pronunciation`
- **Request model:** none (`form` query param).
- **Response model:** raw audio bytes (`fastapi.Response`, dynamic `media_type`), not Pydantic schema.
- **Notable status/error behavior:** `422` validation failures. `404` not found. `503` DB unavailable/locked. `503` runtime errors.

### DELETE `/api/wordbank/database`
- **Request model:** none.
- **Response model:** `ResetDatabaseResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `503` with `Database reset failed: ...` for filesystem/OS failures.
