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
  message: string | null
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
