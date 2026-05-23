# API Contract

All HTTP routes in `backend/app/api/routes/*.py`.

## Contract source

Routes: `backend/app/api/routes/`. DTOs: `backend/app/api/schemas/v1/`.

## Root

### GET `/api/`
- **Request model:** none.
- **Response model:** inline `dict[str, str]` (`{"status": "ok", "message": "danote backend scaffold"}`).
- **Notable status/error behavior:** `200`.

### GET `/api/health`
- **Request model:** none.
- **Response model:** `HealthResponse` (`backend/app/api/schemas/v1/root.py`).
- **Notable status/error behavior:** `200` with `status: "ok"` or `"degraded"` per DB/NLP readiness.

### GET `/api/me`
- **Request model:** none.
- **Response model:** `CurrentUserResponse` (`backend/app/api/schemas/v1/auth.py`).
- **Notable status/error behavior:** `401` missing/invalid bearer token when auth is enabled. Accepts Clerk JWTs and guest bearer tokens. `403` authenticated user is outside the configured allowlist. With auth disabled, returns the local development user.

Unless otherwise noted, non-health app data routes require an authenticated user when `DANOTE_AUTH_ENABLED=1` and scope persisted wordbank/sentencebank data to that user. Guest users get a fresh scoped `app_users` identity per guest session.

## Guest

### POST `/api/guest/sessions`
- **Request model:** `GuestSessionRequest` (`{"browser_id": "<anonymous-browser-id>"}`).
- **Response model:** `GuestSessionResponse` (`{"token": "guest_<opaque>", "auth_provider": "guest", "trial": TrialStatus}`).
- **Notable status/error behavior:** Unauthenticated. Creates a fresh guest user/session and returns a bearer token for app data routes. The browser id is hashed server-side and used only for daily guest quota accounting; guest wordbank/sentencebank rows are scoped to the new session user and are not reused by later guest sessions.

## Account

All `/api/account/*` endpoints require a valid `Authorization: Bearer <clerk-jwt>`
or `Authorization: Bearer <guest-token>` header. Local dev
(`DANOTE_AUTH_ENABLED=0`) bypasses verification and resolves to a fixed dev user.

### GET `/api/account/me`
- **Response model:** `AccountMeResponse` (`backend/app/api/schemas/v1/account.py`).
- **Notable status/error behavior:** `401` missing/invalid token. `403` email not on allowlist (when `DANOTE_ALLOWED_EMAILS` or `DANOTE_ALLOWED_EMAIL_DOMAINS` is set). `503` when auth services failed to initialize.

### GET `/api/account/status`
- **Response model:** `AccountStatusResponse`.
- **Notable status/error behavior:** Returns `keys_configured: true` only when all four providers (`gemini`, `deepl`, `azure_translation`, `azure_tts`) have a stored key. `last_four` is the last 4 chars of the saved value for UI preview. Guest users always return `keys_configured: false`; API-key mutation/test endpoints return `403 guest_api_keys_forbidden`.
- **`trial` block (`TrialStatus`):** `enabled` (feature on for this deployment), `available` (host Gemini key present so hosted-key access can run), `opted_in`, `keys_configured`, `limit`, `used`, `remaining`, `resets_on` (next reset date `YYYY-MM-DD` in `DANOTE_TRIAL_RESET_TIMEZONE`). `used`/`remaining` count distinct words searched today; signed-in no-key users use `DANOTE_TRIAL_DAILY_SEARCH_LIMIT`, guests use `DANOTE_GUEST_DAILY_SEARCH_LIMIT`.

### POST `/api/account/trial/opt-in`
- **Response model:** `TrialOptInResponse` (`{ "trial": TrialStatus }`).
- **Notable status/error behavior:** Idempotent — records trial opt-in for the current user (lets them past the API-keys gate). Returns the refreshed trial status. `401`/`403`/`503` as for other account endpoints.

### DELETE `/api/account/data`
- **Response model:** `AccountFreshStartResponse` (`status: "reset"`, `message`).
- **Notable status/error behavior:** `401`/`403`/`503` as for other account endpoints.
- **Field invariants:** Clears the current user's learning workspace data: wordbank rows, sentencebank rows, phrase translations, ignored tokens, wordbank background jobs, token feedback, typo feedback, and verification change logs. It does not delete API keys, account identity, guest session records, trial opt-in state, or daily search usage.

### PUT `/api/account/api-keys/{provider}`
- **Request model:** `UpdateApiKeyRequest` (`{"value": "<api-key>"}`).
- **Response model:** `UpdateApiKeyResponse`.
- **Notable status/error behavior:** `400` unknown provider or empty value. `503` if `DANOTE_KEY_ENCRYPTION_SECRET` is not configured.

### DELETE `/api/account/api-keys/{provider}`
- **Response model:** `UpdateApiKeyResponse` with `is_set: false`.

### POST `/api/account/api-keys/{provider}/test`
- **Response model:** `TestApiKeyResponse`. Currently only structurally validates the stored key (length). Real outbound calls use the stored key at request time via the per-user service resolver.

## Analyze

### POST `/api/analyze`
- **Request model:** `AnalyzeRequest`.
- **Response model:** `AnalyzeResponse`.
- **Notable status/error behavior:** `503` NLP unavailable by default while the DaCy stack is retired. `503` DB unavailable/locked. `400` validation/value errors.

### POST `/api/analyze/enrich-token`
- **Request model:** `EnrichTokenRequest`.
- **Response model:** `ResolveQueryResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `400` value errors from query resolution.

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
- **Request details:** `english_translation` may be provided by trusted generated-example previews and is persisted without retranslation. `token_persistence_mode` defaults to `auto_save_all`; `link_existing_only` requires `target: {stored_lemma, meaning_id}` and is reserved for generated examples.
- **Field invariants:** response now includes hydrated sentence details (`id`, `created_at`, `tokens[]`, `has_pronunciation`). `tokens[]` carries `token_index`, `surface_form`, `save_status`, nullable `lemma_candidate`, nullable `stored_lemma`, nullable `lexeme_id`, nullable `meaning_id`, POS/morphology, optional gloss, and translation fields. Insert responses may also include `pronunciation` with `status: queued|skipped` plus `sentence_id` when background sentence audio generation is considered. Sentence-created wordbank entries are verified through one sentence-context Gemini batch prompt during save; `queued_verification_targets[]` remains for response compatibility but is empty for this inline sentence verification path. In `link_existing_only` mode, only the requested saved target word is linked; other wordlike tokens are returned and persisted as `save_status = "unsaved"` cards with NLP lemma/POS/morphology metadata for later manual saving.

### POST `/api/sentencebank/example-preview`
- **Request model:** `GenerateExamplePreviewRequest` (`stored_lemma`, `meaning_id`).
- **Response model:** `GenerateExamplePreviewResponse` (`source_text`, `english_translation`).
- **Notable status/error behavior:** `404` target meaning not found. `503` DB unavailable/locked or Gemini example generation unavailable. `400` invalid inputs.
- **Field invariants:** Gemini receives the saved lemma, selected meaning id/key, gloss, translated gloss, English translation, additional translations, POS/morphology, COR lemma index, and saved surface forms. The response is a short Danish sentence plus natural English translation, with the Danish example normalized to start lowercase and omit a trailing period. The preview is not persisted until the client saves it.

### POST `/api/sentencebank/static-example-preview`
- **Request model:** `GenerateStaticExamplePreviewRequest` (`stored_lemma`).
- **Response model:** `GenerateExamplePreviewResponse` (`source_text`, `english_translation`).
- **Notable status/error behavior:** `404` static word not found. `503` DB unavailable/locked. `400` invalid inputs.
- **Field invariants:** currently supports built-in HV question words. Gemini may generate the preview when available; otherwise the backend returns a curated static example. Saving the preview uses normal sentence `auto_save_all` token persistence so static HV metadata is applied.

### GET `/api/sentencebank/sentences`
- **Request model:** none.
- **Response model:** `SentenceListResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked.
- **Field invariants:** each item includes nested `tokens[]` using the same sentence-token card contract as `POST`, plus `has_pronunciation` derived from persisted sentence audio.

### DELETE `/api/sentencebank/sentences/{sentence_id}`
- **Request model:** path `sentence_id`; query `delete_meanings: bool = false`.
- **Response model:** `DeleteSentenceResponse` (`status: "deleted"`, `message`).
- **Notable status/error behavior:** `404` sentence not found. `503` DB unavailable/locked.
- **Field invariants:** deleting the sentence removes its sentence tokens by DB cascade. With `delete_meanings=true`, only meanings linked by this sentence and not linked by any other saved sentence for the same user are deleted. When those meaning deletes touch saved sentence tokens elsewhere, the wordbank delete safeguard sets those tokens to `save_status = "unsaved"` and clears `lexeme_id`, `meaning_id`, `stored_lemma`, and `cor_id` before deleting wordbank rows.

### POST `/api/sentencebank/sentences/{sentence_id}/tokens/{token_index}/save`
- **Request model:** path params only.
- **Response model:** `SaveSentenceTokenResponse` (`SentenceSummary` fields, `saved_token`, `message`, `queued_verification_targets`).
- **Notable status/error behavior:** `404` sentence or token not found. `503` DB unavailable/locked or token save runtime unavailable.
- **Field invariants:** reserved for `save_status = "unsaved"` sentence token cards. The backend resolves only the requested token through the same sentence-token COR/Gemini resolver used by normal `auto_save_all` sentence saves, replaces that token with a saved token, and leaves other unsaved generated-example tokens untouched. New wordbank entries created by this token save are verified through the same inline sentence-context Gemini batch path as sentence inserts; `queued_verification_targets[]` remains for response compatibility but is empty for this path.

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
- **Response model:** `SentenceSearchPreviewResponse` (`status: "ready" | "blocked" | "preview"`, `query_language`, `source_text`, `english_translation`, `is_valid`, `errors`, `message`, `is_multi_word_expression`, `mwe_lemma`, `mwe_pos_tag`, `mwe_gloss`, `mwe_english_translation`, `mwe_cor_match`).
- **Notable status/error behavior:** `422` empty or >100 char text. `503` DB unavailable.
- **Field invariants:**
  - `source_text`: finalized Danish sentence candidate for sidebar display and save. `null` only when preview is blocked.
  - `query_language`: detected language of the original query, not the finalized Danish sentence.
  - `english_translation`: for Danish/unknown queries, derived from the finalized Danish `source_text`; for English-origin queries, the corrected original English sentence used for translation, not a Danish-to-English retranslation.
  - `status = "preview"`: fast preview path. Skips sentence verification, uses heuristic language detection plus the configured translation service, and is intended for immediate sidebar feedback while the full result is still pending.
  - `status = "ready"`: save may proceed when `source_text` is non-null.
  - `status = "blocked"`: sidebar disables save and surfaces `message`.
  - `is_multi_word_expression`: true if the entire query is exactly one multi-word expression (e.g. phrasal verb or idiom).
  - `mwe_lemma`: dictionary form of the MWE if applicable.
  - `mwe_pos_tag`: part of speech of the MWE (e.g., `phrasal_verb` or `idiom`).
  - `mwe_gloss`: brief Danish definition of the MWE.
  - `mwe_english_translation`: English translation of the MWE.
  - `mwe_cor_match`: matched `CORSearchVariant` for the MWE if found in COR, or a synthetically populated one if it is generated.
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

### DELETE `/api/wordbank/meanings/{meaning_id}`
- **Request model:** path `meaning_id`.
- **Response model:** `DeleteMeaningResponse` (`was_lemma_deleted`, `message`).
- **Notable status/error behavior:** `404` meaning not found. `503` DB unavailable/locked.
- **Field invariants:** before deleting a meaning, any owner-scoped sentence tokens referencing that meaning are converted to unsaved tokens by setting `save_status = "unsaved"` and clearing `lexeme_id`, `meaning_id`, `stored_lemma`, and `cor_id`. If the meaning is the last meaning for its lemma, the endpoint deletes the whole lemma and returns `was_lemma_deleted: true`; otherwise it deletes only the meaning and its surface forms.

### DELETE `/api/wordbank/lemmas/{lemma}`
- **Request model:** path `lemma`.
- **Response model:** `DeleteLemmaResponse` (`status: "deleted"`, `message`).
- **Notable status/error behavior:** `404` lemma not found. `503` DB unavailable/locked.
- **Field invariants:** before deleting the lemma and all cascaded wordbank records, any owner-scoped sentence tokens referencing the lemma are converted to unsaved tokens by setting `save_status = "unsaved"` and clearing `lexeme_id`, `meaning_id`, `stored_lemma`, and `cor_id`.

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
  - Requires Gemini and uses one Gemini variation-resolution call for COR, generated non-COR, and unknown meanings.
  - Gated by verification state: returns `skipped` until meaning target + all saved variations are `verified`. `queued`/`error`/`flagged` states return explicit skip messages.
  - The Gemini response is the authoritative variation set; backend persists returned missing forms directly after normalization/dedupe and does not run a follow-up completion verification review. Same-spelling forms are allowed when Gemini returns them for distinct morphology, including forms that match the lemma.
  - `added_surface_forms`: forms inserted. `queued_pronunciation_forms`: forms queued for background pronunciation (lemma-scoped, merged by `stored_lemma`; may include lemma itself).
  - `queued_verification_targets`: empty for this Gemini-resolved completion path; retained for response compatibility.

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
  - Legacy completion-review records may expose meaning-level `fix_variations`; current Complete variations requests resolve and persist variations directly through Gemini and do not create new completion-review records.
  - Generated non-COR meanings can apply legacy structured `fix_variations` without COR identity; apply uses the provided slot forms and removes generated off-slot adjective/verb rows.
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
  - English-only local-dictionary hits return `classification: "new"`, `query_language: "en"`, `query_language_confidence: 0.95`, and populate `en_pos_groups`.
  - `en_pos_groups[]` groups English results by `(lemma, pos_ud)` and preserves POS priority `NOUN`, `VERB`, `ADJ`, `ADV`, `PROPN`, then others.
  - Each `en_pos_groups[]` item carries `lemma`, `pos_ud`, optional `pos_raw`, optional group-level `danish_translation`, and `senses[]`.
  - Each `senses[]` item carries `pos_ud`, `sense_idx`, `gloss`, optional `danish_translation`, and `examples[]`.
  - English dictionary groups are capped to the first five senses per POS group.

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
- **Field invariants:** saved search rows keep lemma translation + gloss translation separate. `english_translation` = saved lemma translation only. `gloss_translation` = optional disambiguation context and is omitted when redundant with the lemma translation, including verb glosses already covered by an infinitive translation. Raw `gloss` not promoted into `english_translation`. Static presaved words may return saved-default rows even when not persisted as DB lexemes; those rows include lemma, translation, POS/morphology, `variation_count=1`, empty `query_cor_ids`, and optional `match_surface` for English matches. `did_you_mean`: non-null when query had no direct matches and a Levenshtein-close wordbank lemma was found; `items` then contains results for the corrected word.

> **Hosted-key metering:** `cor-form`, `cor-form-batch`, and `en-form` count one
> distinct word per day against the free-trial cap for signed-in users who have
> not configured all four API keys, or the guest cap for guest users (auth enabled only). The whole fan-out of a
> single user query collapses to one count via its query key (`en_query` when
> present, else `form`); repeating an already-counted word that day is free.
> Exceeding the cap returns `429` with detail `trial_daily_limit_reached`.
> `cor-lemma/{lemma_idx}` (paradigm drill-in) is not metered.

### GET `/api/wordbank/search/cor-form`
- **Request model:** none (`form`, `limit`, `include_translations`, optional `en_query`/`en_pos_ud` query params).
- **Response model:** `CORSearchFormResponse`.
- **Notable status/error behavior:** `422` validation failures. `503` DB unavailable/locked. `503` runtime errors. `429 trial_daily_limit_reached` when the free-trial daily cap is exceeded.
- **Field invariants:**
  - `lemma_translation` + `gloss_translation` separate; gloss text never promoted into `lemma_translation`.
  - `saveable_translation`: backend-authoritative search save value. Equals `lemma_translation` when usable; may carry gloss-derived fallback when `lemma_translation` is `null`.
  - `lemma_translation_provider`: which provider supplied displayed lemma translation.
  - `lemma_translation_status`: `provider`, `gemini`, `gloss_fallback`, or `missing`.
  - `lemma_translation_reason`: final decision reason (`provider_ok`, `provider_self_translation`, `gemini_ok`, `gemini_missing`, `gemini_self_translation`, `gloss_fallback_used`).
  - Valid Danish words missing from COR may return a synthetic `generated_non_cor` group after Gemini validation. These rows use `dictionary_status = "generated_non_cor"`, have no saveable COR id, and persist through the generated non-COR wordbank flow.
  - DeepL/Azure COR search: same fallback via shared primary-provider contract.
  - Primary framed translation collapses to Danish lemma/form (e.g. `at bile -> to bile`): treated as invalid, prefers Gemini contextual translation.
  - Gloss not required for Gemini fallback; glossless entries send Danish lemma + POS/morphology; verbs framed as infinitives (e.g. `at bile`).
  - Gemini returns non-empty translation: trusted even if English matches Danish lemma exactly.
  - Gemini returns nothing: backend may keep `lemma_translation = null` with gloss-derived `saveable_translation`; no gloss fallback means both stay `null`.
  - `en_query`: when provided, backend may ask Gemini to keep only COR groups whose Danish meaning translates that English query; if Gemini returns no usable match or fails, all COR groups are kept.
  - `did_you_mean`: non-null when `form` had no COR entries and a Levenshtein-close COR lemma was found; `groups` then contains results for the corrected lemma.

### POST `/api/wordbank/search/cor-form-batch`
- **Request model:** `CORSearchFormBatchRequest` (`items[]` of `form`, optional `en_query`, optional `en_pos_ud`; shared `limit` and `include_translations`).
- **Response model:** `CORSearchFormBatchResponse`.
- **Notable status/error behavior:** `422` validation failures. `503` DB unavailable/locked. `503` runtime errors. `429 trial_daily_limit_reached` when the free-trial daily cap is exceeded (the batch counts once, keyed by the shared `en_query`).
- **Field invariants:** equivalent to calling `GET /api/wordbank/search/cor-form` once per item and returning responses in request order. When `en_query` is present, the same Gemini sense-filter safety rule applies: if the filter returns no usable match or fails, that item keeps all COR groups.

### GET `/api/wordbank/search/en-form`
- **Request model:** none (`form`, `include_translations` query params).
- **Response model:** `ENSearchFormResponse`.
- **Notable status/error behavior:** `422` validation failures. `503` DB unavailable/locked. `503` runtime errors. `429 trial_daily_limit_reached` when the free-trial daily cap is exceeded.
- **Field invariants:**
  - Uses only the local English dictionary plus optional EN→DA translation providers for group/sense translations.
  - Missing local dictionary or unmatched `form` returns `groups: []`.
  - `groups[]` uses the same `ENPosGroup` shape as `ResolveQueryResponse.en_pos_groups`.
  - `groups[].form` is the matched English dictionary form for the query, which may be an inflected surface form distinct from `groups[].lemma` (for example `dogs` with lemma `dog`).
  - Groups are keyed by `(lemma, pos_ud)`, preserve POS priority `NOUN`, `VERB`, `ADJ`, `ADV`, `PROPN`, then others, and cap senses to five per POS group.
  - `danish_translation` prefers the matched English surface form translation before lemma translation, and may be `null`; clients must treat null rows as not directly saveable.
  - `meaning_description` is nullable. When a query has two or more distinct Danish translations and Gemini is available, it contains a short English disambiguation label for that translated meaning.

### GET `/api/wordbank/search/cor-lemma/{lemma_idx}`
- **Request model:** none (`lemma_idx` path param, optional `limit` query param).
- **Response model:** `CORLemmaParadigmResponse`.
- **Notable status/error behavior:** `422` path/query validation failures. `503` DB unavailable/locked. `503` runtime errors.

### GET `/api/wordbank/lemmas/{lemma}`
- **Request model:** none (`lemma` path param).
- **Response model:** `LemmaDetailsResponse`.
- **Notable response behavior:**
  - Static presaved words may return detail payloads without a DB lexeme; single-sense payloads are non-sectioned, static homographs are sectioned by built-in POS/sense, and both shapes have empty categories/related/linked sentence lists unless the lexeme has been materialized.
  - Root payload may include `categories`, `verification`, `additional_translations: string[]`, and `reference_links[]`.
  - Each `meaning_sections[]` may include `categories`, `verification`, `gram_raw`, `additional_translations: string[]`, and `reference_links[]`.
  - `reference_links[]` rows contain `page_id`, `page_title`, `tab_id`, `tab_title`, and `sentinel`; clients render these as word-card links to pinned reference tabs without deriving homes from lemma-only matching.
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

### GET `/api/wordbank/numbers/pronunciation`
- **Request model:** none (`term` query param).
- **Response model:** raw audio bytes (`fastapi.Response`, dynamic `media_type`), not Pydantic schema.
- **Notable status/error behavior:** `422` validation failures. `404` not found. `503` DB unavailable/locked.

### POST `/api/wordbank/numbers/pronunciation/seed`
- **Request model:** none (`force: bool = False` query param).
- **Response model:** `SeedNumbersAudioResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked or TTS unavailable. `force=true` regenerates stored number audio.

### GET `/api/wordbank/presaved-words/pronunciation`
- **Request model:** none (`term` query param).
- **Response model:** raw audio bytes (`fastapi.Response`, dynamic `media_type`), not Pydantic schema.
- **Notable status/error behavior:** `422` validation failures. `404` not found. `503` DB unavailable/locked.

### POST `/api/wordbank/presaved-words/pronunciation/seed`
- **Request model:** none (`force: bool = False` query param).
- **Response model:** `SeedPresavedWordsAudioResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked or TTS unavailable. `force=true` regenerates stored presaved-word audio.

### DELETE `/api/wordbank/database`
- **Request model:** none.
- **Response model:** `ResetDatabaseResponse`.
- **Notable status/error behavior:** `503` DB unavailable/locked. `503` with `Database reset failed: ...` for filesystem/OS failures.
