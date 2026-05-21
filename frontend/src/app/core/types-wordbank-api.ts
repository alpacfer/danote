import type { ENPosGroup, LemmaDetailsResponse } from "@/app/core/types-wordbank-details-api"

export type SearchSaveSeed = {
  lemma: string
  surface: string
  cor_id?: string | null
  cor_lemma_idx?: number | null
  dictionary_status?: "cor" | "generated_non_cor" | "unknown" | null
  meaning_key?: string | null
  gloss?: string | null
  english_translation?: string | null
  pos_tag?: string | null
  morphology?: string | null
  target_meaning_id?: number | null
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

export type FindAlternativeTranslationsResponse = {
  status: "updated" | "skipped" | "error"
  stored_lemma: string
  meaning_id: number | null
  primary_translation: string | null
  added_additional_translations: string[]
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

export type VerificationChangeEntry = {
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
}

export type GetVerificationChangesResponse = {
  items: VerificationChangeEntry[]
}

export type RevertVerificationChangeResponse = {
  status: "reverted" | "already_reverted" | "not_found"
  change_id: number
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
  did_you_mean?: string | null
}

export type CORSearchVariant = {
  cor_id: string
  form: string
  lemma: string
  dictionary_status?: "cor" | "generated_non_cor" | "unknown"
  gloss?: string | null
  gloss_translation?: string | null
  english_source_description?: string | null
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
  did_you_mean?: string | null
}

export type CORSearchFormBatchResponse = {
  items: CORSearchFormResponse[]
}

export type ENSearchFormResponse = {
  form: string
  groups: ENPosGroup[]
}
