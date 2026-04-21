import { vi } from "vitest"

import { responseOf } from "./render-helpers"

import { type AnalyzeToken, buildWordActionsFromResolvePayload, type ResolveQueryPayload } from "./mock-fetch-types"

function buildQueuedVerificationTargets(response: {
  stored_lemma: string
  stored_surface_form: string | null
  meaning?: { id: number } | null
}) {
  const targets: Array<{ meaning_id: number | null; stored_surface_form: string | null }> = []
  const pushTarget = (meaningId: number | null, storedSurfaceForm: string | null) => {
    if (targets.some((target) => target.meaning_id === meaningId && target.stored_surface_form === storedSurfaceForm)) {
      return
    }
    targets.push({ meaning_id: meaningId, stored_surface_form: storedSurfaceForm })
  }

  if (response.meaning?.id != null) {
    pushTarget(response.meaning.id, null)
    if (response.stored_surface_form && response.stored_surface_form !== response.stored_lemma) {
      pushTarget(response.meaning.id, response.stored_surface_form)
    }
    return targets
  }

  pushTarget(null, null)
  if (response.stored_surface_form && response.stored_surface_form !== response.stored_lemma) {
    pushTarget(null, response.stored_surface_form)
  }
  return targets
}

type MockVerificationAction = {
  action_type: "fix_translation" | "fix_variations" | "move_to_meaning_section" | "move_to_lemma"
  reason?: string | null
  english_translation?: string | null
  singular_indefinite_forms?: string[] | null
  singular_indefinite_n_word_forms?: string[] | null
  singular_indefinite_t_word_forms?: string[] | null
  singular_definite_forms?: string[] | null
  plural_indefinite_forms?: string[] | null
  plural_definite_forms?: string[] | null
  infinitive_forms?: string[] | null
  present_forms?: string[] | null
  past_forms?: string[] | null
  imperative_forms?: string[] | null
  past_participle_forms?: string[] | null
  target_meaning_id?: number | null
  target_lemma?: string | null
  target_meaning_key?: string | null
  target_gloss?: string | null
  target_english_translation?: string | null
  target_pos_tag?: string | null
  target_morphology?: string | null
}

type MockVerification = {
  status: "verified" | "flagged" | "error" | "skipped" | "queued"
  provider: string | null
  reviewer_role: string | null
  review_intent?: string | null
  message: string
  composed_word_count: number | null
  stored_surface_form?: string | null
  requested_at?: string | null
  completed_at?: string | null
  problem?: string | null
  change_to_implement?: string | null
  suggested_actions?: MockVerificationAction[] | null
}

export function mockFetchImplementation(options?: {
  healthOk?: boolean
  healthStatus?: "ok" | "degraded"
  healthResponse?: Record<string, unknown>
  analyzeOk?: boolean
  analyzeTokens?: AnalyzeToken[]
  analyzeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  addWordOk?: boolean
  addWordResponse?: {
    status: "inserted" | "exists"
    stored_lemma: string
    stored_surface_form: string | null
    source: "manual"
    message: string
    meaning?: {
      id: number
      meaning_key: string
      gloss?: string | null
      english_translation?: string | null
    } | null
    verification?: MockVerification | null
    pronunciation?: {
      status: "queued" | "skipped"
      form: string | null
    } | null
    queued_verification_targets?: Array<{
      meaning_id?: number | null
      stored_surface_form?: string | null
    }>
    queued_pronunciation_forms?: string[]
    saved_snapshot?: {
      lemma: string
      dictionary_status?: "cor" | "generated_non_cor" | "unknown"
      english_translation?: string | null
      additional_translations?: string[]
      pos_tag?: string | null
      morphology?: string | null
      is_sectioned?: boolean
      categories?: string[]
      verification?: MockVerification | null
      related_words?: {
        status: "queued" | "ready" | "empty" | "error"
        message?: string | null
        items: Array<{
          id: number
          relation_type: "compound_component" | "compound_host"
          lemma: string
          english_translation?: string | null
          pos_tag?: string | null
          saved_match: {
            status: "unsaved" | "saved_lemma" | "saved_variation"
            target_lemma?: string | null
            target_meaning_id?: number | null
          }
          display_variant?: {
            cor_id: string
            form: string
            lemma: string
            gloss?: string | null
            gram_raw: string
            lemma_idx: number
            gram_code: number
            variation: number
            pos_tag?: string | null
            morphology?: string | null
            features?: Record<string, string>
            extra_tags?: string[]
            saveable_translation?: string | null
            lemma_translation?: string | null
          } | null
          candidate_variants?: Array<{
            cor_id: string
            form: string
            lemma: string
            gloss?: string | null
            gram_raw: string
            lemma_idx: number
            gram_code: number
            variation: number
            pos_tag?: string | null
            morphology?: string | null
            features?: Record<string, string>
            extra_tags?: string[]
            saveable_translation?: string | null
            lemma_translation?: string | null
          }>
        }>
      }
      meaning_sections?: Array<{
        id: number
        meaning_key: string
        dictionary_status?: "cor" | "generated_non_cor" | "unknown"
        gloss?: string | null
        english_translation?: string | null
        additional_translations?: string[]
        gloss_translation?: string | null
        pos_tag?: string | null
        morphology?: string | null
        gram_raw?: string | null
        categories?: string[]
        verification?: MockVerification | null
        surface_forms: Array<{
          form: string
          has_pronunciation?: boolean
          pos_tag?: string | null
          morphology?: string | null
          lemma?: string | null
          lemma_translation?: string | null
          gloss?: string | null
          gloss_translation?: string | null
          gram_raw?: string | null
          verification?: MockVerification | null
        }>
      }>
      surface_forms: Array<{
        form: string
        has_pronunciation?: boolean
        pos_tag?: string | null
        morphology?: string | null
        lemma?: string | null
        lemma_translation?: string | null
        gloss?: string | null
        gloss_translation?: string | null
        gram_raw?: string | null
        verification?: MockVerification | null
      }>
    } | null
  }
  verifyWordResponse?: {
    stored_lemma: string
    stored_surface_form: string | null
    verification: MockVerification
    applied_categories?: string[]
  }
  verifyWordHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  queueVerificationResponse?: {
    stored_lemma: string
    stored_surface_form: string | null
    meaning_id: number | null
    review_intent: string
    verification: MockVerification
  }
  queueVerificationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  completeVariationsResponse?: {
    status: "updated" | "skipped"
    stored_lemma: string
    meaning_id: number
    added_surface_forms: string[]
    queued_pronunciation_forms: string[]
    queued_verification_targets: Array<{
      meaning_id: number | null
      stored_surface_form: string | null
    }>
    message: string
  }
  completeVariationsHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  rethinkCategoriesResponse?: {
    status: "updated" | "skipped" | "error"
    stored_lemma: string
    stored_surface_form: string | null
    meaning_id: number | null
    applied_categories: string[]
    message: string
  }
  rethinkCategoriesHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  findAlternativeTranslationsResponse?: {
    status: "updated" | "skipped" | "error"
    stored_lemma: string
    meaning_id: number | null
    primary_translation: string | null
    added_additional_translations: string[]
    message: string
  }
  findAlternativeTranslationsHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  applyVerificationChangesResponse?: {
    status: "applied" | "skipped"
    stored_lemma: string
    stored_surface_form: string | null
    applied_action_type: string | null
    target_lemma: string | null
    target_meaning_id: number | null
  }
  applyVerificationChangesHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  verificationChangesResponse?: {
    items: Array<{
      id: number
      stored_lemma: string
      stored_surface_form: string | null
      meaning_id: number | null
      action_type: string
      before_json: Record<string, unknown>
      after_json: Record<string, unknown>
      applied_at: string
      reverted_at: string | null
      provider: string | null
    }>
  }
  verificationChangesHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  revertVerificationChangeResponse?: {
    status: "reverted" | "already_reverted" | "not_found"
    change_id: number
  }
  revertVerificationChangeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  addWordHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmasOk?: boolean
  lemmasResponse?: {
    items: Array<{
      lemma: string
      variation_count: number
      english_translation?: string | null
    }>
  }
  searchWordbankResponse?: {
    items: Array<{
      lemma: string
      display_lemma: string
      meaning_id?: number | null
      meaning_key?: string | null
      gloss?: string | null
      gloss_translation?: string | null
      cor_lemma_idx?: number | null
      variation_count: number
      english_translation?: string | null
      match_surface?: string | null
      query_cor_ids?: string[]
      pos_tag?: string | null
      morphology?: string | null
    }>
  }
  corSearchFormResponse?: {
    form: string
    did_you_mean?: string | null
    groups: Array<{
      lemma: string
      gloss?: string | null
      pos_tag?: string | null
      variants: Array<{
        cor_id: string
        form: string
        lemma: string
        gloss?: string | null
        gloss_translation?: string | null
        lemma_translation?: string | null
        saveable_translation?: string | null
        lemma_translation_provider?: string | null
        lemma_translation_status?: "provider" | "gemini" | "gloss_fallback" | "missing" | null
        lemma_translation_reason?: string | null
        gram_raw: string
        norm?: string | null
        lemma_idx: number
        gram_code: number
        variation: number
        pos_tag?: string | null
        morphology?: string | null
        features?: Record<string, string>
        extra_tags?: string[]
      }>
    }>
  }
  corSearchFormHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  wordbankSearchHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmaDetailsOk?: boolean
  lemmaDetailsHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmaDetailsResponse?: {
    lemma: string
    dictionary_status?: "cor" | "generated_non_cor" | "unknown"
    english_translation?: string | null
    additional_translations?: string[]
    pos_tag?: string | null
    morphology?: string | null
    is_sectioned?: boolean
    categories?: string[]
    verification?: MockVerification | null
    related_words?: {
      status: "queued" | "ready" | "empty" | "error"
      message?: string | null
      items: Array<{
        id: number
        relation_type: "compound_component" | "compound_host"
        lemma: string
        english_translation?: string | null
        pos_tag?: string | null
        saved_match: {
          status: "unsaved" | "saved_lemma" | "saved_variation"
          target_lemma?: string | null
          target_meaning_id?: number | null
        }
        display_variant?: {
          cor_id: string
          form: string
          lemma: string
          gloss?: string | null
          gram_raw: string
          lemma_idx: number
          gram_code: number
          variation: number
          pos_tag?: string | null
          morphology?: string | null
          features?: Record<string, string>
          extra_tags?: string[]
          saveable_translation?: string | null
          lemma_translation?: string | null
        } | null
        candidate_variants?: Array<{
          cor_id: string
          form: string
          lemma: string
          gloss?: string | null
          gram_raw: string
          lemma_idx: number
          gram_code: number
          variation: number
          pos_tag?: string | null
          morphology?: string | null
          features?: Record<string, string>
          extra_tags?: string[]
          saveable_translation?: string | null
          lemma_translation?: string | null
        }>
      }>
    }
    meaning_sections?: Array<{
      id: number
      meaning_key: string
      dictionary_status?: "cor" | "generated_non_cor" | "unknown"
      gloss?: string | null
      english_translation?: string | null
      additional_translations?: string[]
      gloss_translation?: string | null
      pos_tag?: string | null
      morphology?: string | null
      gram_raw?: string | null
      categories?: string[]
      verification?: MockVerification | null
      surface_forms: Array<{
        form: string
        has_pronunciation?: boolean
        pos_tag?: string | null
        morphology?: string | null
        lemma?: string | null
        lemma_translation?: string | null
        gloss?: string | null
        gloss_translation?: string | null
        gram_raw?: string | null
        verification?: MockVerification | null
      }>
    }>
    surface_forms: Array<{
      form: string
      has_pronunciation?: boolean
      pos_tag?: string | null
      morphology?: string | null
      lemma?: string | null
      lemma_translation?: string | null
      gloss?: string | null
      gloss_translation?: string | null
      gram_raw?: string | null
    }>
  }
  resetDbOk?: boolean
  resetDbResponse?: {
    status: "reset"
    message: string
  }
  resetDbHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  developerApiKeysResponse?: {
    status: string
    message: string
    configured: Record<string, boolean>
  }
  developerApiKeysHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  translationProbeResponse?: {
    status: string
    probe_input: string
    result_text: string | null
    provider: string | null
    message: string
  }
  translationProbeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  speechProbeResponse?: {
    status: string
    probe_input: string
    result_text: string | null
    provider: string | null
    message: string
  }
  speechProbeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  pronunciationAudioHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  geminiProbeResponse?: {
    status: string
    probe_input: string
    result_text: string | null
    provider: string | null
    message: string
  }
  geminiProbeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  translationResponse?: {
    status: "generated" | "unavailable"
    source_word: string
    lemma: string
    english_translation: string | null
  }
  resolveQueryResponse?: {
    query_surface: string
    query_lemma: string | null
    classification: "known" | "variation" | "typo_likely" | "uncertain" | "new"
    matched_lemma: string | null
    matched_lemma_summary: {
      lemma: string
      english_translation: string | null
      variation_count: number
    } | null
    query_pos_tag: string | null
    query_morphology: string | null
    resolved_surface: string
    resolved_lemma: string | null
    da_to_en_translation: string | null
    en_to_da_translation: string | null
    en_to_da_lemma: string | null
    en_to_da_pos_tag: string | null
    en_to_da_morphology: string | null
    query_language: "en" | "da" | "ambiguous" | null
    query_language_confidence: number | null
    en_pos_groups?: Array<{
      lemma: string
      pos_ud: string
      pos_raw?: string | null
      danish_translation?: string | null
      senses: Array<{
        pos_ud: string
        sense_idx: number
        gloss: string
        danish_translation?: string | null
        examples: string[]
      }>
    }>
    word_actions: Array<{
      action_type: "open_wordbank" | "add_as_new" | "add_variation"
      surface: string
      lemma: string
      cor_id?: string | null
      translation_label: string | null
      direction: "da_to_en" | "en_to_da" | "variation" | "known"
      direction_label: string | null
      pos_tag: string | null
      morphology: string | null
      show_lemma: boolean
    }>
  }
  resolveQueryHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  enrichTokenResponse?: {
    query_surface: string
    query_lemma: string | null
    classification: "known" | "variation" | "typo_likely" | "uncertain" | "new"
    matched_lemma: string | null
    matched_lemma_summary: {
      lemma: string
      english_translation: string | null
      variation_count: number
    } | null
    query_pos_tag: string | null
    query_morphology: string | null
    resolved_surface: string
    resolved_lemma: string | null
    da_to_en_translation: string | null
    en_to_da_translation: string | null
    en_to_da_lemma: string | null
    en_to_da_pos_tag: string | null
    en_to_da_morphology: string | null
    query_language: "en" | "da" | "ambiguous" | null
    query_language_confidence: number | null
    word_actions?: Array<{
      action_type: "open_wordbank" | "add_as_new" | "add_variation"
      surface: string
      lemma: string
      cor_id?: string | null
      translation_label: string | null
      direction: "da_to_en" | "en_to_da" | "variation" | "known"
      direction_label: string | null
      pos_tag: string | null
      morphology: string | null
      show_lemma: boolean
    }>
  }
  enrichTokenHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  translationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  phraseTranslationResponse?: {
    status: "generated" | "unavailable"
    source_text: string
    english_translation: string | null
  }
  phraseTranslationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  reverseTranslationResponse?: {
    status: "generated" | "unavailable"
    source_word: string
    danish_translation: string | null
  }
  reverseTranslationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  detectLanguageResponse?: {
    source_word: string
    language: "en" | "da" | "ambiguous"
    confidence: number
  }
  detectLanguageHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  sentencebankOk?: boolean
  sentencebankResponse?: {
    items: Array<{
      id: number
      source_text: string
      english_translation?: string | null
      created_at: string
      has_pronunciation?: boolean
      tokens?: Array<{
        token_index: number
        surface_form: string
        stored_lemma: string
        lexeme_id: number
        meaning_id?: number | null
        pos_tag?: string | null
        morphology?: string | null
        gloss?: string | null
        english_translation?: string | null
        gloss_translation?: string | null
      }>
    }>
  }
  sentencebankHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  addSentenceOk?: boolean
  addSentenceResponse?: {
    status: "inserted" | "exists"
    id?: number
    source_text: string
    english_translation: string | null
    created_at?: string
    has_pronunciation?: boolean
    tokens?: Array<{
      token_index: number
      surface_form: string
      stored_lemma: string
      lexeme_id: number
      meaning_id?: number | null
      pos_tag?: string | null
      morphology?: string | null
      gloss?: string | null
      english_translation?: string | null
      gloss_translation?: string | null
    }>
    message: string
    pronunciation?: {
      status: "queued" | "skipped"
      sentence_id: number
    } | null
  }
  addSentenceHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  sentencePronunciationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  sentencePronunciationAudioHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  verifySentenceResponse?: {
    is_valid: boolean
    errors: Array<{ start: number; end: number; message: string }>
    corrected_text: string | null
    language: "da" | "en" | "unknown"
  }
  verifySentenceOk?: boolean
  verifySentenceHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  sentenceSearchPreviewResponse?: {
    status: "ready" | "blocked" | "preview"
    query_language: "da" | "en" | "unknown"
    source_text: string | null
    english_translation: string | null
    is_valid: boolean
    errors: Array<{ start: number; end: number; message: string }>
    message: string | null
  }
  sentenceSearchPreviewFastResponse?: {
    status: "ready" | "blocked" | "preview"
    query_language: "da" | "en" | "unknown"
    source_text: string | null
    english_translation: string | null
    is_valid: boolean
    errors: Array<{ start: number; end: number; message: string }>
    message: string | null
  }
  sentenceSearchPreviewOk?: boolean
  sentenceSearchPreviewHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
}) {
  const healthOk = options?.healthOk ?? true
  const healthStatus = options?.healthStatus ?? "ok"
  const healthResponse = options?.healthResponse ?? {
    status: healthStatus,
    service: "backend",
    apis: {
      backend: { status: healthStatus === "ok" ? "ok" : "degraded", active: true, configured: true },
      deepl_translator: {
        status: "inactive",
        active: false,
        configured: false,
        message: "Provider 'deepl' is not selected.",
      },
      azure_translator: {
        status: "inactive",
        active: false,
        configured: false,
        message: "Provider 'azure' is not selected.",
      },
      azure_speech: {
        status: "inactive",
        active: false,
        configured: false,
        message: "Provider 'azure' is not selected.",
      },
      gemini: {
        status: "inactive",
        active: false,
        configured: false,
        message: "Gemini has not been checked yet.",
      },
    },
  }
  const analyzeOk = options?.analyzeOk ?? true
  const analyzeTokens = options?.analyzeTokens ?? []
  const addWordOk = options?.addWordOk ?? true
  const addWordResponseBase = options?.addWordResponse ?? {
    status: "inserted" as const,
    stored_lemma: "kat",
    stored_surface_form: "kat",
    source: "manual" as const,
    message: "Added 'kat' to wordbank.",
    verification: {
      status: "queued" as const,
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      message: "Queued",
      composed_word_count: null,
    },
  }
  const addWordResponse = {
    ...addWordResponseBase,
    queued_verification_targets: addWordResponseBase.queued_verification_targets ?? buildQueuedVerificationTargets(addWordResponseBase),
    queued_pronunciation_forms: addWordResponseBase.queued_pronunciation_forms ?? [],
  }
  const verifyWordResponse = options?.verifyWordResponse ?? {
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: addWordResponse.stored_surface_form,
    verification: {
      status: "verified" as const,
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      review_intent: "general",
      message: "Entry looks correct.",
      composed_word_count: 1,
    },
    applied_categories: [],
  }
  const queueVerificationResponse = options?.queueVerificationResponse ?? {
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: addWordResponse.stored_surface_form,
    meaning_id: addWordResponse.meaning?.id ?? null,
    review_intent: "general",
    verification: {
      status: "queued" as const,
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      review_intent: "general",
      message: "Queued",
      composed_word_count: null,
      stored_surface_form: addWordResponse.stored_surface_form,
      requested_at: "2026-03-15T12:00:00.000Z",
    },
  }
  const completeVariationsResponse = options?.completeVariationsResponse ?? {
    status: "updated" as const,
    stored_lemma: addWordResponse.stored_lemma,
    meaning_id: addWordResponse.meaning?.id ?? 1,
    added_surface_forms: [],
    queued_pronunciation_forms: [],
    queued_verification_targets: [{ meaning_id: addWordResponse.meaning?.id ?? 1, stored_surface_form: null }],
    message: `Completed noun variations for '${addWordResponse.stored_lemma}'.`,
  }
  const rethinkCategoriesResponse = options?.rethinkCategoriesResponse ?? {
    status: "updated" as const,
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: null,
    meaning_id: null,
    applied_categories: ["Animals"],
    message: `Updated categories for '${addWordResponse.stored_lemma}'.`,
  }
  const findAlternativeTranslationsResponse = options?.findAlternativeTranslationsResponse ?? {
    status: "updated" as const,
    stored_lemma: addWordResponse.stored_lemma,
    meaning_id: null,
    primary_translation: null,
    added_additional_translations: ["alternate"],
    message: `Added 1 alternative translation for '${addWordResponse.stored_lemma}'.`,
  }
  const applyVerificationChangesResponse = options?.applyVerificationChangesResponse ?? {
    status: "applied" as const,
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: addWordResponse.stored_surface_form,
    applied_action_type: "fix_translation",
    target_lemma: addWordResponse.stored_lemma,
    target_meaning_id: null,
  }
  const verificationChangesResponse = options?.verificationChangesResponse ?? {
    items: [],
  }
  const revertVerificationChangeResponse = options?.revertVerificationChangeResponse ?? {
    status: "reverted" as const,
    change_id: 1,
  }
  const lemmasOk = options?.lemmasOk ?? true
  const lemmasResponse = options?.lemmasResponse ?? { items: [] }
  const searchWordbankResponse = options?.searchWordbankResponse ?? {
    items: lemmasResponse.items.map((item) => ({
      lemma: item.lemma,
      display_lemma: item.lemma,
      meaning_id: 1,
      meaning_key: item.lemma,
      gloss: null,
      cor_lemma_idx: null,
      english_translation: item.english_translation ?? null,
      variation_count: item.variation_count,
      match_surface: null,
      query_cor_ids: [],
    })),
  }
  const corSearchFormResponse = options?.corSearchFormResponse ?? {
    form: "kat",
    groups: [],
  }
  const lemmaDetailsOk = options?.lemmaDetailsOk ?? true
  const lemmaDetailsResponse = options?.lemmaDetailsResponse
  const resetDbOk = options?.resetDbOk ?? true
  const resetDbResponse = options?.resetDbResponse ?? { status: "reset" as const, message: "Database reset complete." }
  const developerApiKeysResponse = options?.developerApiKeysResponse ?? {
    status: "updated",
    message: "Runtime API keys updated.",
    configured: {
      gemini: true,
      translation_azure: false,
      translation_deepl: true,
      tts_azure: false,
      word_verification_gemini: true,
    },
  }
  const geminiProbeResponse = options?.geminiProbeResponse ?? {
    status: "ok",
    probe_input: "bogen",
    result_text: "the book",
    provider: "gemini_word_translation",
    message: "Gemini probe completed successfully.",
  }
  const translationProbeResponse = options?.translationProbeResponse ?? {
    status: "ok",
    probe_input: "bogen",
    result_text: "the book",
    provider: "deepl_translator",
    message: "DeepL Translator probe completed successfully.",
  }
  const speechProbeResponse = options?.speechProbeResponse ?? {
    status: "ok",
    probe_input: "bogen",
    result_text: "audio/wav (128 bytes)",
    provider: "azure_speech_tts",
    message: "Azure Speech probe completed successfully.",
  }
  const pronunciationAudioContentType = "audio/wav"
  const pronunciationAudioBytes = new Uint8Array([82, 73, 70, 70, 0, 0, 0, 0, 87, 65, 86, 69])
  const translationResponse = options?.translationResponse ?? {
    status: "unavailable" as const,
    source_word: "kat",
    lemma: "kat",
    english_translation: null,
  }
  const phraseTranslationResponse = options?.phraseTranslationResponse ?? {
    status: "generated" as const,
    source_text: "Jeg elsker dansk",
    english_translation: "I love Danish",
  }
  const reverseTranslationResponse = options?.reverseTranslationResponse ?? {
    status: "unavailable" as const,
    source_word: "house",
    danish_translation: null,
  }
  const resolveQueryResponse = options?.resolveQueryResponse ?? {
    query_surface: "kat",
    query_lemma: "kat",
    classification: "new" as const,
    matched_lemma: null,
    matched_lemma_summary: null,
    query_pos_tag: null,
    query_morphology: null,
    resolved_surface: "kat",
    resolved_lemma: "kat",
    da_to_en_translation: null,
    en_to_da_translation: null,
    en_to_da_lemma: null,
    en_to_da_pos_tag: null,
    en_to_da_morphology: null,
    query_language: null,
    query_language_confidence: null,
    en_pos_groups: [],
    word_actions: [
      {
        action_type: "add_as_new",
        surface: "kat",
        lemma: "kat",
        translation_label: "kat",
        direction: "da_to_en",
        direction_label: "Danish -> English",
        pos_tag: null,
        morphology: null,
        show_lemma: false,
      },
    ],
  }
  if (options?.resolveQueryResponse && !options.resolveQueryResponse.word_actions) {
    throw new Error(
      "mockFetchImplementation requires explicit resolveQueryResponse.word_actions to avoid drifting from backend behavior.",
    )
  }
  if (lemmaDetailsResponse) {
    assertWordbankContractDetails("lemmaDetailsResponse", lemmaDetailsResponse)
  }
  if (addWordResponse.saved_snapshot) {
    assertWordbankContractDetails("addWordResponse.saved_snapshot", addWordResponse.saved_snapshot)
  }
  const detectLanguageResponse = options?.detectLanguageResponse ?? {
    source_word: "house",
    language: "ambiguous" as const,
    confidence: 0.4,
  }
  const sentencebankOk = options?.sentencebankOk ?? true
  const sentencebankResponse = options?.sentencebankResponse ?? { items: [] }
  const addSentenceOk = options?.addSentenceOk ?? true
  const addSentenceResponse = options?.addSentenceResponse ?? {
    status: "inserted" as const,
    id: 1,
    source_text: "Jeg elsker dansk",
    english_translation: "I love Danish",
    created_at: "2026-03-15T12:00:00.000Z",
    has_pronunciation: false,
    tokens: [],
    message: "Added sentence.",
    pronunciation: {
      status: "queued" as const,
      sentence_id: 1,
    },
  }
  const verifySentenceResponse = options?.verifySentenceResponse ?? {
    is_valid: true,
    errors: [],
    corrected_text: null,
    language: "unknown" as const,
  }
  const sentenceSearchPreviewResponse = options?.sentenceSearchPreviewResponse ?? {
    status: "ready" as const,
    query_language: "da" as const,
    source_text: "Jeg elsker dansk",
    english_translation: "I love Danish",
    is_valid: true,
    errors: [],
    message: null,
  }
  const sentenceSearchPreviewFastResponse = options?.sentenceSearchPreviewFastResponse ?? {
    ...sentenceSearchPreviewResponse,
    status: sentenceSearchPreviewResponse.status === "blocked" ? "blocked" as const : "preview" as const,
  }

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith("/api/health")) {
      if (!healthOk) {
        throw new Error("network down")
      }
      return responseOf(healthResponse)
    }

    if (url.endsWith("/api/analyze")) {
      if (options?.analyzeHandler) {
        return options.analyzeHandler(input, init)
      }
      if (!analyzeOk) {
        throw new Error("analyze request failed")
      }
      return responseOf({ tokens: analyzeTokens })
    }

    if (url.endsWith("/api/analyze/enrich-token")) {
      if (options?.enrichTokenHandler) {
        return options.enrichTokenHandler(input, init)
      }
      if (options?.enrichTokenResponse) {
        return responseOf(options.enrichTokenResponse)
      }

      const body = JSON.parse(String(init?.body ?? "{}")) as { token?: string }
      const requestedToken = String(body.token ?? "").trim().toLocaleLowerCase("da-DK")
      let token: AnalyzeToken | null = null
      if (options?.analyzeHandler) {
        const tryTexts = [`${requestedToken} `, requestedToken]
        for (const textValue of tryTexts) {
          const analyzed = await options.analyzeHandler(input, {
            method: "POST",
            body: JSON.stringify({ text: textValue }),
          })
          const analyzedPayload = (await analyzed.json()) as { tokens?: AnalyzeToken[] }
          token = analyzedPayload.tokens?.find(
            (candidate) => (candidate.normalized_token ?? candidate.surface_token ?? "").toLocaleLowerCase("da-DK") === requestedToken,
          ) ?? analyzedPayload.tokens?.[0] ?? null
          if (token) {
            break
          }
        }
      } else {
        token = analyzeTokens.find(
          (candidate) => (candidate.normalized_token ?? candidate.surface_token ?? "").toLocaleLowerCase("da-DK") === requestedToken,
        ) ?? analyzeTokens[0] ?? null
      }

      const responsePayload: ResolveQueryPayload = {
        query_surface: token?.normalized_token ?? requestedToken,
        query_lemma: token?.lemma_candidate ?? null,
        classification: token?.classification ?? "new",
        matched_lemma: token?.matched_lemma ?? null,
        matched_lemma_summary: token?.matched_lemma
          ? {
            lemma: token.matched_lemma,
            english_translation:
              lemmasResponse.items.find((item) => item.lemma === token?.matched_lemma)?.english_translation ?? null,
            variation_count: lemmasResponse.items.find((item) => item.lemma === token?.matched_lemma)?.variation_count ?? 0,
          }
          : null,
        query_pos_tag: token?.pos_tag ?? null,
        query_morphology: token?.morphology ?? null,
        resolved_surface: token?.normalized_token ?? requestedToken,
        resolved_lemma: token?.lemma_candidate ?? null,
        da_to_en_translation: token?.classification === "known" || token?.classification === "variation" ? translationResponse.english_translation : null,
        en_to_da_translation: null,
        en_to_da_lemma: null,
        en_to_da_pos_tag: null,
        en_to_da_morphology: null,
        query_language: null,
        query_language_confidence: null,
      }
      return responseOf({
        ...responsePayload,
        word_actions: buildWordActionsFromResolvePayload(responsePayload),
      })
    }

    if (url.endsWith("/api/wordbank/lexemes")) {
      if (options?.addWordHandler) {
        return options.addWordHandler(input, init)
      }
      if (!addWordOk) {
        throw new Error("add word request failed")
      }
      return responseOf(addWordResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/verify")) {
      if (options?.verifyWordHandler) {
        return options.verifyWordHandler(input, init)
      }
      return responseOf(verifyWordResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/queue-verification")) {
      if (options?.queueVerificationHandler) {
        return options.queueVerificationHandler(input, init)
      }
      return responseOf(queueVerificationResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/complete-variations")) {
      if (options?.completeVariationsHandler) {
        return options.completeVariationsHandler(input, init)
      }
      return responseOf(completeVariationsResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/rethink-categories")) {
      if (options?.rethinkCategoriesHandler) {
        return options.rethinkCategoriesHandler(input, init)
      }
      return responseOf(rethinkCategoriesResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/find-alternative-translations")) {
      if (options?.findAlternativeTranslationsHandler) {
        return options.findAlternativeTranslationsHandler(input, init)
      }
      return responseOf(findAlternativeTranslationsResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/apply-verification-changes")) {
      if (options?.applyVerificationChangesHandler) {
        return options.applyVerificationChangesHandler(input, init)
      }
      return responseOf(applyVerificationChangesResponse)
    }

    if (url.includes("/api/wordbank/lexemes/verification-changes?")) {
      if (options?.verificationChangesHandler) {
        return options.verificationChangesHandler(input, init)
      }
      return responseOf(verificationChangesResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/revert-verification-change")) {
      if (options?.revertVerificationChangeHandler) {
        return options.revertVerificationChangeHandler(input, init)
      }
      return responseOf(revertVerificationChangeResponse)
    }

    if (url.endsWith("/api/wordbank/lexemes/pronunciation")) {
      const body = JSON.parse(String(init?.body ?? "{}")) as {
        stored_lemma?: string
        stored_surface_form?: string | null
      }
      return responseOf({
        status: "generated",
        stored_lemma: body.stored_lemma ?? "kat",
        stored_surface_form: body.stored_surface_form ?? "kat",
        pronunciation_form: body.stored_surface_form ?? body.stored_lemma ?? null,
      })
    }

    if (url.includes("/api/wordbank/pronunciation?")) {
      if (options?.pronunciationAudioHandler) {
        return options.pronunciationAudioHandler(input, init)
      }
      return new Response(pronunciationAudioBytes, {
        status: 200,
        headers: {
          "Content-Type": pronunciationAudioContentType,
        },
      })
    }

    if (url.endsWith("/api/wordbank/lemmas")) {
      if (!lemmasOk) {
        throw new Error("wordbank request failed")
      }
      return responseOf(lemmasResponse)
    }

    if (url.includes("/api/wordbank/search?")) {
      if (options?.wordbankSearchHandler) {
        return options.wordbankSearchHandler(input, init)
      }
      const parsed = new URL(url, "http://localhost")
      const query = (parsed.searchParams.get("query") ?? "").trim().toLocaleLowerCase("da-DK")
      if (!query) {
        return responseOf({ items: [] })
      }
      const filtered = searchWordbankResponse.items.filter((item) => {
        const lemma = item.lemma.trim().toLocaleLowerCase("da-DK")
        const translation = (item.english_translation ?? "").trim().toLocaleLowerCase("da-DK")
        const surface = (item.match_surface ?? "").trim().toLocaleLowerCase("da-DK")
        return lemma.includes(query) || translation.includes(query) || surface.includes(query)
      })
      return responseOf({ items: filtered })
    }

    if (url.includes("/api/wordbank/search/cor-form?")) {
      if (options?.corSearchFormHandler) {
        return options.corSearchFormHandler(input, init)
      }
      const parsed = new URL(url, "http://localhost")
      const form = (parsed.searchParams.get("form") ?? "").trim().toLocaleLowerCase("da-DK")
      if (!form) {
        return responseOf({ form: "", groups: [] })
      }
      if (form === corSearchFormResponse.form.toLocaleLowerCase("da-DK")) {
        return responseOf(corSearchFormResponse)
      }
      return responseOf({ form, groups: [] })
    }

    if (url.includes("/api/wordbank/lemmas/")) {
      if (options?.lemmaDetailsHandler) {
        return options.lemmaDetailsHandler(input, init)
      }
      if (!lemmaDetailsOk) {
        throw new Error("word details request failed")
      }
      if (!lemmaDetailsResponse) {
        throw new Error(
          "mockFetchImplementation requires explicit lemmaDetailsResponse or lemmaDetailsHandler for /api/wordbank/lemmas/* requests.",
        )
      }
      return responseOf(lemmaDetailsResponse)
    }

    if (url.endsWith("/api/wordbank/database")) {
      if (options?.resetDbHandler) {
        return options.resetDbHandler(input, init)
      }
      if (!resetDbOk) {
        throw new Error("reset database request failed")
      }
      return responseOf(resetDbResponse)
    }

    if (url.endsWith("/api/tokens/feedback")) {
      return responseOf({ status: "recorded" })
    }

    if (url.endsWith("/api/tokens/ignore")) {
      return responseOf({ status: "ignored" })
    }


    if (url.endsWith("/api/wordbank/resolve-query")) {
      if (options?.resolveQueryHandler) {
        return options.resolveQueryHandler(input, init)
      }
      if (options?.resolveQueryResponse) {
        return responseOf(resolveQueryResponse)
      }

      const body = JSON.parse(String(init?.body ?? "{}")) as { query_text?: string }
      const query = String(body.query_text ?? "").trim().toLocaleLowerCase("da-DK")

      let token: AnalyzeToken | null = null
      if (options?.analyzeHandler) {
        const analyzed = await options.analyzeHandler(input, {
          method: "POST",
          body: JSON.stringify({ text: query }),
        })
        const analyzedPayload = (await analyzed.json()) as { tokens?: AnalyzeToken[] }
        token = analyzedPayload.tokens?.[0] ?? null
      } else {
        token = analyzeTokens[0] ?? null
      }

      const querySurface = token?.normalized_token ?? query
      const queryLemma = token?.lemma_candidate ?? token?.lemma ?? null
      const classification = token?.classification ?? "new"

      let daToEn = translationResponse.english_translation
      if (options?.translationHandler) {
        const translated = await options.translationHandler(input, {
          method: "POST",
          body: JSON.stringify({ surface_token: querySurface, lemma_candidate: queryLemma }),
        })
        const translatedPayload = (await translated.json()) as { english_translation?: string | null }
        daToEn = translatedPayload.english_translation ?? null
      }

      let enToDa = reverseTranslationResponse.danish_translation
      if (options?.reverseTranslationHandler) {
        const reversed = await options.reverseTranslationHandler(input, {
          method: "POST",
          body: JSON.stringify({ source_word: query }),
        })
        const reversedPayload = (await reversed.json()) as { danish_translation?: string | null }
        enToDa = reversedPayload.danish_translation ?? null
      }

      let language = detectLanguageResponse.language
      let confidence = detectLanguageResponse.confidence
      if (options?.detectLanguageHandler) {
        const detected = await options.detectLanguageHandler(input, {
          method: "POST",
          body: JSON.stringify({ source_word: query }),
        })
        const detectedPayload = (await detected.json()) as { language?: "en" | "da" | "ambiguous"; confidence?: number }
        language = detectedPayload.language ?? detectLanguageResponse.language
        confidence = detectedPayload.confidence ?? detectLanguageResponse.confidence
      }

      const responsePayload: ResolveQueryPayload = {
        query_surface: querySurface,
        query_lemma: queryLemma,
        classification,
        matched_lemma: token?.matched_lemma ?? null,
        matched_lemma_summary: token?.matched_lemma
          ? {
            lemma: token.matched_lemma,
            english_translation:
              lemmasResponse.items.find((item) => item.lemma === token?.matched_lemma)?.english_translation ?? null,
            variation_count: lemmasResponse.items.find((item) => item.lemma === token?.matched_lemma)?.variation_count ?? 0,
          }
          : null,
        query_pos_tag: token?.pos_tag ?? null,
        query_morphology: token?.morphology ?? null,
        resolved_surface: querySurface,
        resolved_lemma: queryLemma,
        da_to_en_translation: daToEn,
        en_to_da_translation: enToDa,
        en_to_da_lemma: null,
        en_to_da_pos_tag: null,
        en_to_da_morphology: null,
        query_language: language,
        query_language_confidence: confidence,
      }
      return responseOf({
        ...responsePayload,
        word_actions: buildWordActionsFromResolvePayload(responsePayload),
      })
    }

    if (url.endsWith("/api/wordbank/translation")) {
      if (options?.translationHandler) {
        return options.translationHandler(input, init)
      }
      return responseOf(translationResponse)
    }

    if (url.endsWith("/api/wordbank/phrase-translation")) {
      if (options?.phraseTranslationHandler) {
        return options.phraseTranslationHandler(input, init)
      }
      return responseOf(phraseTranslationResponse)
    }

    if (url.endsWith("/api/wordbank/reverse-translation")) {
      if (options?.reverseTranslationHandler) {
        return options.reverseTranslationHandler(input, init)
      }
      return responseOf(reverseTranslationResponse)
    }

    if (url.endsWith("/api/wordbank/detect-language")) {
      if (options?.detectLanguageHandler) {
        return options.detectLanguageHandler(input, init)
      }
      return responseOf(detectLanguageResponse)
    }

    if (url.endsWith("/api/developer/api-keys")) {
      if (options?.developerApiKeysHandler) {
        return options.developerApiKeysHandler(input, init)
      }
      return responseOf(developerApiKeysResponse)
    }

    if (url.endsWith("/api/developer/gemini-probe")) {
      if (options?.geminiProbeHandler) {
        return options.geminiProbeHandler(input, init)
      }
      return responseOf(geminiProbeResponse)
    }

    if (url.endsWith("/api/developer/translation-probe")) {
      if (options?.translationProbeHandler) {
        return options.translationProbeHandler(input, init)
      }
      return responseOf(translationProbeResponse)
    }

    if (url.endsWith("/api/developer/tts-probe")) {
      if (options?.speechProbeHandler) {
        return options.speechProbeHandler(input, init)
      }
      return responseOf(speechProbeResponse)
    }

    if (url.endsWith("/api/sentencebank/search-preview")) {
      if (options?.sentenceSearchPreviewHandler) {
        return options.sentenceSearchPreviewHandler(input, init)
      }
      if (options?.sentenceSearchPreviewOk === false) {
        throw new Error("sentence search preview request failed")
      }
      const body = JSON.parse(String(init?.body ?? "{}")) as { fast?: boolean }
      return responseOf(body.fast ? sentenceSearchPreviewFastResponse : sentenceSearchPreviewResponse)
    }

    if (url.endsWith("/api/sentencebank/verify-sentence")) {
      if (options?.verifySentenceHandler) {
        return options.verifySentenceHandler(input, init)
      }
      if (options?.verifySentenceOk === false) {
        throw new Error("verify sentence request failed")
      }
      return responseOf(verifySentenceResponse)
    }

    if (url.endsWith("/api/sentencebank/sentences") && init?.method === "POST") {
      if (options?.addSentenceHandler) {
        return options.addSentenceHandler(input, init)
      }
      if (!addSentenceOk) {
        throw new Error("add sentence request failed")
      }
      return responseOf(addSentenceResponse)
    }

    if (url.endsWith("/api/sentencebank/sentences/pronunciation")) {
      if (options?.sentencePronunciationHandler) {
        return options.sentencePronunciationHandler(input, init)
      }
      const body = JSON.parse(String(init?.body ?? "{}")) as { sentence_id?: number }
      return responseOf({
        status: "generated",
        sentence_id: body.sentence_id ?? 1,
        source_text: addSentenceResponse.source_text,
      })
    }

    if (url.includes("/api/sentencebank/pronunciation?")) {
      if (options?.sentencePronunciationAudioHandler) {
        return options.sentencePronunciationAudioHandler(input, init)
      }
      return new Response(pronunciationAudioBytes, {
        status: 200,
        headers: {
          "Content-Type": pronunciationAudioContentType,
        },
      })
    }

    if (url.endsWith("/api/sentencebank/sentences")) {
      if (options?.sentencebankHandler) {
        return options.sentencebankHandler(input, init)
      }
      if (!sentencebankOk) {
        throw new Error("sentencebank request failed")
      }
      return responseOf(sentencebankResponse)
    }

    return { ok: false, status: 404 } as Response
  })
}

function assertWordbankContractDetails(name: string, payload: unknown) {
  if (!payload || typeof payload !== "object") {
    throw new Error(`mockFetchImplementation expected ${name} to be an object.`)
  }
  const candidate = payload as {
    lemma?: unknown
    surface_forms?: unknown
    meaning_sections?: unknown
    is_sectioned?: unknown
  }
  if (typeof candidate.lemma !== "string" || candidate.lemma.trim().length === 0) {
    throw new Error(`mockFetchImplementation expected ${name}.lemma to be a non-empty string.`)
  }
  if (!Array.isArray(candidate.surface_forms)) {
    throw new Error(`mockFetchImplementation expected ${name}.surface_forms to be an array.`)
  }
  if (candidate.is_sectioned === true && !Array.isArray(candidate.meaning_sections)) {
    throw new Error(`mockFetchImplementation expected ${name}.meaning_sections to be an array for sectioned word pages.`)
  }
  if (!Array.isArray(candidate.meaning_sections ?? [])) {
    throw new Error(`mockFetchImplementation expected ${name}.meaning_sections to be an array when provided.`)
  }
  const meaningSections = (candidate.meaning_sections ?? []) as unknown[]
  for (const [index, section] of meaningSections.entries()) {
    if (!section || typeof section !== "object") {
      throw new Error(`mockFetchImplementation expected ${name}.meaning_sections[${index}] to be an object.`)
    }
    const typedSection = section as { id?: unknown; meaning_key?: unknown; surface_forms?: unknown }
    if (typeof typedSection.id !== "number") {
      throw new Error(`mockFetchImplementation expected ${name}.meaning_sections[${index}].id to be a number.`)
    }
    if (typeof typedSection.meaning_key !== "string" || typedSection.meaning_key.trim().length === 0) {
      throw new Error(`mockFetchImplementation expected ${name}.meaning_sections[${index}].meaning_key to be a non-empty string.`)
    }
    if (!Array.isArray(typedSection.surface_forms)) {
      throw new Error(`mockFetchImplementation expected ${name}.meaning_sections[${index}].surface_forms to be an array.`)
    }
  }
}
