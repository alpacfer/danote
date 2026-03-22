export type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
export type ApiRuntimeStatus = "ok" | "degraded" | "inactive" | "missing_key" | "disabled" | "unknown"
export type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
export type AppSection = "playground" | "notes" | "wordbank" | "sentencebank" | "developer"
export type TokenAction = "add_as_new"

export type SearchSaveSeed = {
  lemma: string
  surface: string
  cor_id?: string | null
  cor_lemma_idx?: number | null
  meaning_key?: string | null
  gloss?: string | null
  english_translation?: string | null
  pos_tag?: string | null
  morphology?: string | null
  target_meaning_id?: number | null
}

export type WordActionSuggestion = {
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
}

export type AnalyzedToken = {
  surface_token: string
  normalized_token: string
  lemma_candidate: string | null
  pos_tag: string | null
  morphology: string | null
  classification: TokenClassification
  match_source: "exact" | "lemma" | "none"
  matched_lemma: string | null
  matched_surface_form: string | null
  suggestions: Array<{
    value: string
    score: number
    source_flags: string[]
  }>
  confidence: number
  reason_tags: string[]
  word_actions?: WordActionSuggestion[]
}

export type AddWordResponse = {
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
  verification?: VerificationResult | null
  queued_verification_targets?: Array<{
    meaning_id: number | null
    stored_surface_form: string | null
  }>
  queued_pronunciation_forms?: string[]
  pronunciation?: {
    status: "queued" | "skipped"
    form: string | null
  } | null
  saved_snapshot?: LemmaDetailsResponse | null
}

export type VerificationAction = {
  action_type: "fix_translation" | "fix_gloss" | "fix_variations" | "move_to_meaning_section" | "move_to_lemma"
  reason?: string | null
  english_translation?: string | null
  gloss?: string | null
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
  singular_definite_form?: string | null
  plural_indefinite_form?: string | null
  plural_definite_form?: string | null
  target_meaning_id?: number | null
  target_lemma?: string | null
  target_meaning_key?: string | null
  target_gloss?: string | null
  target_english_translation?: string | null
  target_pos_tag?: string | null
  target_morphology?: string | null
}

export type VerificationResult = {
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
  suggested_actions?: VerificationAction[] | null
}

export type VerifyWordResponse = {
  stored_lemma: string
  stored_surface_form: string | null
  verification: VerificationResult
  applied_categories: string[]
}

export type QueueVerificationResponse = {
  stored_lemma: string
  stored_surface_form: string | null
  meaning_id: number | null
  review_intent: string
  verification: VerificationResult
}

export type RethinkCategoriesResponse = {
  status: "updated" | "skipped" | "error"
  stored_lemma: string
  stored_surface_form: string | null
  meaning_id: number | null
  applied_categories: string[]
  message: string
}

export type CompleteVariationsResponse = {
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

export type GeneratePronunciationResponse = {
  status: "generated" | "unavailable" | "skipped"
  stored_lemma: string
  stored_surface_form: string | null
  pronunciation_form: string | null
}

export type ApplyVerificationChangesResponse = {
  status: "applied" | "skipped"
  stored_lemma: string
  stored_surface_form: string | null
  applied_action_type: string | null
  target_lemma: string | null
  target_meaning_id: number | null
}

export type WordbankLemma = {
  lemma: string
  display_lemma?: string | null
  english_translation: string | null
  variation_count: number
  pos_tag?: string | null
  morphology?: string | null
}

export type LemmaListResponse = {
  items: WordbankLemma[]
}

export type WordbankSearchItem = {
  lemma: string
  display_lemma: string
  meaning_id: number | null
  meaning_key: string | null
  gloss: string | null
  gloss_translation?: string | null
  cor_lemma_idx: number | null
  english_translation: string | null
  variation_count: number
  match_surface?: string | null
  query_cor_ids?: string[]
  pos_tag?: string | null
  morphology?: string | null
}

export type WordbankSearchResponse = {
  items: WordbankSearchItem[]
}

export type CORSearchVariant = {
  cor_id: string
  form: string
  lemma: string
  gloss?: string | null
  gloss_translation?: string | null
  lemma_translation?: string | null
  gram_raw: string
  norm?: string | null
  lemma_idx: number
  gram_code: number
  variation: number
  pos_tag?: string | null
  morphology?: string | null
  features: Record<string, string>
  extra_tags: string[]
}

export type CORSearchGroup = {
  lemma: string
  gloss?: string | null
  pos_tag?: string | null
  variants: CORSearchVariant[]
}

export type CORSearchFormResponse = {
  form: string
  groups: CORSearchGroup[]
}

export type LemmaDetailsResponse = {
  lemma: string
  english_translation: string | null
  pos_tag: string | null
  morphology: string | null
  is_sectioned?: boolean
  categories?: string[]
  verification?: VerificationResult | null
  meaning_sections?: Array<{
    id: number
    meaning_key: string
    gloss?: string | null
    english_translation?: string | null
    gloss_translation?: string | null
    pos_tag?: string | null
    morphology?: string | null
    gram_raw?: string | null
    categories?: string[]
    verification?: VerificationResult | null
    surface_forms: Array<{
      form: string
      pos_tag: string | null
      morphology: string | null
      lemma?: string | null
      lemma_translation?: string | null
      gloss?: string | null
      gloss_translation?: string | null
      gram_raw?: string | null
      has_pronunciation?: boolean
      verification?: VerificationResult | null
    }>
  }>
  surface_forms: Array<{
    form: string
    pos_tag: string | null
    morphology: string | null
    lemma?: string | null
    lemma_translation?: string | null
    gloss?: string | null
    gloss_translation?: string | null
    gram_raw?: string | null
    has_pronunciation?: boolean
    verification?: VerificationResult | null
  }>
}

export type ResetDatabaseResponse = {
  status: "reset"
  message: string
}

export type GenerateTranslationResponse = {
  status: "generated" | "unavailable"
  source_word: string
  lemma: string
  english_translation: string | null
}

export type ResolveQueryResponse = {
  query_surface: string
  query_lemma: string | null
  classification: TokenClassification
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
  word_actions?: WordActionSuggestion[]
}

export type GeneratePhraseTranslationResponse = {
  status: "generated" | "cached" | "unavailable"
  source_text: string
  english_translation: string | null
}

export type SentencebankSentence = {
  id: number
  source_text: string
  english_translation: string | null
  created_at: string
}

export type SentenceListResponse = {
  items: SentencebankSentence[]
}

export type AddSentenceResponse = {
  status: "inserted" | "exists"
  source_text: string
  english_translation: string | null
  message: string
}

export type HealthApiStatusEntry = {
  status?: string
  active?: boolean
  configured?: boolean
  message?: string | null
}

export type HealthPayload = {
  status?: string
  service?: string
  components?: Record<string, string>
  apis?: Record<string, HealthApiStatusEntry>
}

export type ApiStatusItem = {
  name: string
  label: string
  status: ApiRuntimeStatus
  message: string | null
}

export type DeveloperApiKeysUpdateResponse = {
  status: string
  message: string
  configured: Record<string, boolean>
}

export type DeveloperServiceProbeResponse = {
  status: string
  probe_input: string
  result_text: string | null
  provider: string | null
  message: string
}

export type GeminiProbeResponse = DeveloperServiceProbeResponse

export type TokenFeedbackPayload = {
  raw_token: string
  predicted_status: string
  suggestions_shown: string[]
  user_action: TokenAction
  chosen_value?: string
  source?: "playground" | "search"
}

export type SearchFeedbackContext = {
  rawToken: string
  predictedStatus: TokenClassification
  suggestionsShown: string[]
}
