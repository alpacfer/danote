import { vi } from "vitest"

import { responseOf } from "./render-helpers"

import { type AnalyzeToken, buildWordActionsFromResolvePayload, type ResolveQueryPayload } from "./mock-fetch-types"

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
    verification?: {
      status: "verified" | "flagged" | "error" | "skipped" | "queued"
      provider: string | null
      reviewer_role: string | null
      message: string
      composed_word_count: number | null
      stored_surface_form?: string | null
      requested_at?: string | null
      completed_at?: string | null
      problem?: string | null
      change_to_implement?: string | null
      suggested_actions?: Array<{
        action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
        reason?: string | null
        english_translation?: string | null
        gloss?: string | null
        target_meaning_id?: number | null
        target_lemma?: string | null
        target_meaning_key?: string | null
        target_gloss?: string | null
        target_english_translation?: string | null
        target_pos_tag?: string | null
        target_morphology?: string | null
      }> | null
    } | null
    pronunciation?: {
      status: "queued" | "skipped"
      form: string | null
    } | null
    saved_snapshot?: {
      lemma: string
      english_translation?: string | null
      pos_tag?: string | null
      morphology?: string | null
      is_sectioned?: boolean
      verification?: {
        status: "verified" | "flagged" | "error" | "skipped" | "queued"
        provider: string | null
        reviewer_role: string | null
        message: string
        composed_word_count: number | null
        stored_surface_form?: string | null
        requested_at?: string | null
        completed_at?: string | null
        problem?: string | null
        change_to_implement?: string | null
        suggested_actions?: Array<{
          action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
          reason?: string | null
          english_translation?: string | null
          gloss?: string | null
          target_meaning_id?: number | null
          target_lemma?: string | null
          target_meaning_key?: string | null
          target_gloss?: string | null
          target_english_translation?: string | null
          target_pos_tag?: string | null
          target_morphology?: string | null
        }> | null
      } | null
      meaning_sections?: Array<{
        id: number
        meaning_key: string
        gloss?: string | null
        english_translation?: string | null
        gloss_translation?: string | null
        pos_tag?: string | null
        morphology?: string | null
        verification?: {
          status: "verified" | "flagged" | "error" | "skipped" | "queued"
          provider: string | null
          reviewer_role: string | null
          message: string
          composed_word_count: number | null
          stored_surface_form?: string | null
          requested_at?: string | null
          completed_at?: string | null
          problem?: string | null
          change_to_implement?: string | null
          suggested_actions?: Array<{
            action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
            reason?: string | null
            english_translation?: string | null
            gloss?: string | null
            target_meaning_id?: number | null
            target_lemma?: string | null
            target_meaning_key?: string | null
            target_gloss?: string | null
            target_english_translation?: string | null
            target_pos_tag?: string | null
            target_morphology?: string | null
          }> | null
        } | null
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
    } | null
  }
  verifyWordResponse?: {
    stored_lemma: string
    stored_surface_form: string | null
    verification: {
      status: "verified" | "flagged" | "error" | "skipped" | "queued"
      provider: string | null
      reviewer_role: string | null
      message: string
      composed_word_count: number | null
      stored_surface_form?: string | null
      requested_at?: string | null
      completed_at?: string | null
      problem?: string | null
      change_to_implement?: string | null
      suggested_actions?: Array<{
        action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
        reason?: string | null
        english_translation?: string | null
        gloss?: string | null
        target_meaning_id?: number | null
        target_lemma?: string | null
        target_meaning_key?: string | null
        target_gloss?: string | null
        target_english_translation?: string | null
        target_pos_tag?: string | null
        target_morphology?: string | null
      }> | null
    }
  }
  verifyWordHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  applyVerificationChangesResponse?: {
    status: "applied" | "skipped"
    stored_lemma: string
    stored_surface_form: string | null
    applied_action_type: string | null
    target_lemma: string | null
    target_meaning_id: number | null
  }
  applyVerificationChangesHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
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
    groups: Array<{
      lemma: string
      gloss?: string | null
      pos_tag?: string | null
      variants: Array<{
        cor_id: string
        form: string
        lemma: string
        gloss?: string | null
        lemma_translation?: string | null
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
  lemmaDetailsOk?: boolean
  lemmaDetailsHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmaDetailsResponse?: {
    lemma: string
    english_translation?: string | null
    is_sectioned?: boolean
    verification?: {
      status: "verified" | "flagged" | "error" | "skipped" | "queued"
      provider: string | null
      reviewer_role: string | null
      message: string
      composed_word_count: number | null
      stored_surface_form?: string | null
      requested_at?: string | null
      completed_at?: string | null
      problem?: string | null
      change_to_implement?: string | null
      suggested_actions?: Array<{
        action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
        reason?: string | null
        english_translation?: string | null
        gloss?: string | null
        target_meaning_id?: number | null
        target_lemma?: string | null
        target_meaning_key?: string | null
        target_gloss?: string | null
        target_english_translation?: string | null
        target_pos_tag?: string | null
        target_morphology?: string | null
      }> | null
    } | null
    meaning_sections?: Array<{
      id: number
      meaning_key: string
      gloss?: string | null
      english_translation?: string | null
      gloss_translation?: string | null
      pos_tag?: string | null
      morphology?: string | null
      verification?: {
        status: "verified" | "flagged" | "error" | "skipped" | "queued"
        provider: string | null
        reviewer_role: string | null
        message: string
        composed_word_count: number | null
        stored_surface_form?: string | null
        requested_at?: string | null
        completed_at?: string | null
        problem?: string | null
        change_to_implement?: string | null
        suggested_actions?: Array<{
          action_type: "fix_translation" | "fix_gloss" | "move_to_meaning_section" | "move_to_lemma"
          reason?: string | null
          english_translation?: string | null
          gloss?: string | null
          target_meaning_id?: number | null
          target_lemma?: string | null
          target_meaning_key?: string | null
          target_gloss?: string | null
          target_english_translation?: string | null
          target_pos_tag?: string | null
          target_morphology?: string | null
        }> | null
      } | null
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
    }>
  }
  addSentenceOk?: boolean
  addSentenceResponse?: {
    status: "inserted" | "exists"
    source_text: string
    english_translation: string | null
    message: string
  }
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
  const addWordResponse = options?.addWordResponse ?? {
    status: "inserted" as const,
    stored_lemma: "kat",
    stored_surface_form: "kat",
    source: "manual" as const,
    message: "Added 'kat' to wordbank.",
    verification: {
      status: "queued" as const,
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      message: "Word verification queued.",
      composed_word_count: null,
    },
  }
  const verifyWordResponse = options?.verifyWordResponse ?? {
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: addWordResponse.stored_surface_form,
    verification: {
      status: "verified" as const,
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      message: "Entry looks correct.",
      composed_word_count: 1,
    },
  }
  const applyVerificationChangesResponse = options?.applyVerificationChangesResponse ?? {
    status: "applied" as const,
    stored_lemma: addWordResponse.stored_lemma,
    stored_surface_form: addWordResponse.stored_surface_form,
    applied_action_type: "fix_translation",
    target_lemma: addWordResponse.stored_lemma,
    target_meaning_id: null,
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
  const lemmaDetailsResponse = options?.lemmaDetailsResponse ?? {
    lemma: "bog",
    english_translation: null,
    surface_forms: [{ form: "bogen" }],
  }
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
    source_text: "Jeg elsker dansk",
    english_translation: "I love Danish",
    message: "Added sentence.",
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

    if (url.endsWith("/api/wordbank/lexemes/apply-verification-changes")) {
      if (options?.applyVerificationChangesHandler) {
        return options.applyVerificationChangesHandler(input, init)
      }
      return responseOf(applyVerificationChangesResponse)
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
        return responseOf({
        ...resolveQueryResponse,
        word_actions: resolveQueryResponse.word_actions ?? buildWordActionsFromResolvePayload(resolveQueryResponse),
      })
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

    if (url.endsWith("/api/sentencebank/sentences") && init?.method === "POST") {
      if (!addSentenceOk) {
        throw new Error("add sentence request failed")
      }
      return responseOf(addSentenceResponse)
    }

    if (url.endsWith("/api/sentencebank/sentences")) {
      if (!sentencebankOk) {
        throw new Error("sentencebank request failed")
      }
      return responseOf(sentencebankResponse)
    }

    return { ok: false, status: 404 } as Response
  })
}
