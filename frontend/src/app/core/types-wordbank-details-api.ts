import type { TokenClassification, WordActionSuggestion } from "@/app/core/types-app-api"
import type { SentenceTokenCard } from "@/app/core/types-sentencebank"
import type { CORSearchVariant, VerificationResult } from "@/app/core/types-wordbank-api"

export type LemmaDetailsResponse = {
  dictionary_status?: "cor" | "generated_non_cor" | "unknown"
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
      display_variant?: CORSearchVariant | null
      candidate_variants?: CORSearchVariant[]
    }>
  }
  linked_sentences?: Array<{
    id: number
    source_text: string
    english_translation?: string | null
    created_at: string
    matched_token_indexes?: number[]
    tokens: SentenceTokenCard[]
  }>
  lemma: string
  english_translation: string | null
  additional_translations?: string[]
  pos_tag: string | null
  morphology: string | null
  is_sectioned?: boolean
  categories?: string[]
  verification?: VerificationResult | null
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
  en_pos_groups?: ENPosGroup[]
}

export type ENSenseOut = {
  pos_ud: string
  sense_idx: number
  gloss: string
  danish_translation: string | null
  examples: string[]
}

export type ENPosGroup = {
  lemma: string
  pos_ud: string
  pos_raw: string | null
  danish_translation: string | null
  senses: ENSenseOut[]
}
