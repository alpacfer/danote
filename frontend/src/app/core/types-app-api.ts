export type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
export type ApiRuntimeStatus = "ok" | "degraded" | "inactive" | "missing_key" | "disabled" | "unknown"
export type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
export type AppSection = "wordbank" | "sentencebank" | "developer"
export type TokenAction = "add_as_new"

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

export type TokenFeedbackPayload = {
  raw_token: string
  predicted_status: string
  suggestions_shown: string[]
  user_action: TokenAction
  chosen_value?: string
  source?: "search"
}

export type SearchFeedbackContext = {
  rawToken: string
  predictedStatus: TokenClassification
  suggestionsShown: string[]
}
