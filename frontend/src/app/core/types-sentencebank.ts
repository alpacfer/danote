import type { CORSearchVariant } from "./types-wordbank-api"

export interface SentenceVerificationErrorItem {
  start: number
  end: number
  message: string
}

export interface VerifySentenceResponse {
  is_valid: boolean
  errors: SentenceVerificationErrorItem[]
  corrected_text: string | null
  language: "da" | "en" | "unknown"
}

export type SentenceSearchPreviewResponse = {
  status: "ready" | "blocked" | "preview"
  query_language: "da" | "en" | "unknown"
  source_text: string | null
  english_translation: string | null
  is_valid: boolean
  errors: SentenceVerificationErrorItem[]
  corrected_text?: string | null
  message: string | null
  is_multi_word_expression?: boolean
  mwe_lemma?: string | null
  mwe_pos_tag?: string | null
  mwe_gloss?: string | null
  mwe_english_translation?: string | null
  mwe_cor_match?: CORSearchVariant | null
  /** Distinct senses for polysemous MWE lemmas (e.g. "tage på" → put on / gain
   * weight / go somewhere). Monosemous MWEs have a one-element list. The
   * frontend renders one search card per entry; saving each creates a separate
   * meaning row under the same MWE lexeme. Empty when not an MWE. */
  mwe_meanings?: CORSearchVariant[]
}

export type SentenceTokenCard = {
  token_index: number
  surface_form: string
  save_status?: "saved" | "unsaved"
  lemma_candidate?: string | null
  stored_lemma: string | null
  lexeme_id: number | null
  meaning_id: number | null
  pos_tag: string | null
  morphology: string | null
  gloss: string | null
  english_translation: string | null
  gloss_translation: string | null
}

export type SentencebankSentence = {
  id: number
  source_text: string
  english_translation: string | null
  created_at: string
  has_pronunciation?: boolean
  tokens?: SentenceTokenCard[]
}

export type SentenceListResponse = {
  items: SentencebankSentence[]
}

export type AddSentenceResponse = {
  id?: number
  status: "inserted" | "exists"
  source_text: string
  english_translation: string | null
  created_at?: string
  has_pronunciation?: boolean
  tokens?: SentenceTokenCard[]
  message: string
  pronunciation?: {
    status: "queued" | "skipped"
    sentence_id: number
  } | null
  queued_verification_targets?: Array<{
    stored_lemma: string
    meaning_id: number | null
    stored_surface_form: string | null
  }>
}

export type SaveSentenceTokenResponse = SentencebankSentence & {
  saved_token: SentenceTokenCard
  message: string
  queued_verification_targets?: Array<{
    stored_lemma: string
    meaning_id: number | null
    stored_surface_form: string | null
  }>
}

export type GenerateExamplePreviewResponse = {
  source_text: string
  english_translation: string
}

export type GenerateSentencePronunciationResponse = {
  status: "generated" | "unavailable" | "skipped"
  sentence_id: number
  source_text: string
}

export type DeleteSentenceResponse = {
  status: "deleted"
  message: string
}
