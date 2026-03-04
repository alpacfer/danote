export type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
export type ApiRuntimeStatus = "ok" | "degraded" | "inactive" | "missing_key" | "disabled" | "unknown"
export type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
export type AppSection = "playground" | "notes" | "wordbank" | "sentencebank" | "developer"
export type TokenAction = "add_as_new"

export type WordActionSuggestion = {
  action_type: "open_wordbank" | "add_as_new" | "add_variation"
  surface: string
  lemma: string
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
  verification?: {
    status: "verified" | "flagged" | "error" | "skipped" | "queued"
    provider: string | null
    reviewer_role: string | null
    message: string
    composed_word_count: number | null
    problem?: string | null
    change_to_implement?: string | null
    suggested_changes?: {
      lemma_pos_tag?: string | null
      lemma_morphology?: string | null
      surface_pos_tag?: string | null
      surface_morphology?: string | null
      lexeme_translation?: string | null
      surface_translation?: string | null
    } | null
  } | null
}

export type VerifyWordResponse = {
  stored_lemma: string
  stored_surface_form: string | null
  verification: {
    status: "verified" | "flagged" | "error" | "skipped" | "queued"
    provider: string | null
    reviewer_role: string | null
    message: string
    composed_word_count: number | null
    problem?: string | null
    change_to_implement?: string | null
    suggested_changes?: {
      lemma_pos_tag?: string | null
      lemma_morphology?: string | null
      surface_pos_tag?: string | null
      surface_morphology?: string | null
      lexeme_translation?: string | null
      surface_translation?: string | null
    } | null
  }
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
  applied_fields: string[]
}

export type WordbankLemma = {
  lemma: string
  display_lemma?: string | null
  english_translation: string | null
  variation_count: number
}

export type LemmaListResponse = {
  items: WordbankLemma[]
}

export type WordbankSearchItem = {
  lemma: string
  display_lemma: string
  english_translation: string | null
  variation_count: number
  match_surface?: string | null
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
  surface_forms: Array<{
    form: string
    english_translation: string | null
    pos_tag: string | null
    morphology: string | null
    lemma?: string | null
    lemma_translation?: string | null
    gloss?: string | null
    gloss_translation?: string | null
    gram_raw?: string | null
    has_pronunciation?: boolean
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

export type HighlightPopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  tokenIndex: number | null
}

export type PhrasePopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  selectedText: string
}

export type DiscoveredTokenMetadata = {
  pos_tag: string
  morphology: string | null
  lemma: string | null
  word_actions?: WordActionSuggestion[]
}

export type DiscoveredTokenMemory = {
  latest: DiscoveredTokenMetadata
  byPos: Record<string, DiscoveredTokenMetadata>
}

export type SaveDialogMode = "initial" | "create_new"

export type SavedNote = {
  id: string
  name: string
  text: string
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  savedAt: string
}

export type AppNotification = {
  id: string
  message: string
  createdAt: string
  read: boolean
}

export type VerificationErrorDetail = {
  provider: string
  status: "flagged" | "error"
  problem: string
  changeToImplement: string
  rawMessage: string
  storedSurfaceForm: string | null
  suggestedChanges?: {
    lemmaPosTag?: string
    lemmaMorphology?: string
    surfacePosTag?: string
    surfaceMorphology?: string
    lexemeTranslation?: string
    surfaceTranslation?: string
  }
  suggestedChangesPayload?: {
    lemma_pos_tag?: string | null
    lemma_morphology?: string | null
    surface_pos_tag?: string | null
    surface_morphology?: string | null
    lexeme_translation?: string | null
    surface_translation?: string | null
  }
}

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
export const ANALYZE_DEBOUNCE_MS = 450
export const SEARCH_RESOLVE_DEBOUNCE_MS = 220
export const POPOVER_ENRICH_CACHE_TTL_MS = 60_000
export const PHRASE_TRANSLATION_DELAY_MS = 1000
export const NLP_MODEL_OPTIONS = [
  "da_dacy_small_trf-0.2.0",
  "da_dacy_medium_trf-0.2.0",
  "da_dacy_large_trf-0.2.0",
] as const
export const POPOVER_VIEWPORT_MARGIN_PX = 12
export const POPOVER_ESTIMATED_HEIGHT_PX = 280
export const PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS = "max-w-[42ch]"
export const SAVED_NOTES_STORAGE_KEY = "danote.saved-notes.v1"
export const NOTE_AUTOSAVE_DEBOUNCE_MS = 900

export type NlpModelOption = (typeof NLP_MODEL_OPTIONS)[number]

export function loadSavedNotes(): SavedNote[] {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const raw = window.localStorage.getItem(SAVED_NOTES_STORAGE_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter((item): item is SavedNote => {
      if (!item || typeof item !== "object") {
        return false
      }
      const candidate = item as Partial<SavedNote>
      return (
        typeof candidate.id === "string" &&
        typeof candidate.name === "string" &&
        typeof candidate.text === "string" &&
        typeof candidate.savedAt === "string" &&
        Array.isArray(candidate.tokens) &&
        candidate.discoveredTokenMetadata !== null &&
        typeof candidate.discoveredTokenMetadata === "object" &&
        candidate.generatedTranslationMap !== null &&
        typeof candidate.generatedTranslationMap === "object"
      )
    })
  } catch {
    return []
  }
}

export function persistSavedNotes(notes: SavedNote[]) {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.setItem(SAVED_NOTES_STORAGE_KEY, JSON.stringify(notes))
}

export function createSavedNoteId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `note-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function createNotificationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `notification-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function formatSavedNoteTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

export function previewText(value: string, maxLength = 180): string {
  const normalized = value.replace(/\s+/gu, " ").trim()
  if (!normalized) {
    return "No text saved."
  }
  if (normalized.length <= maxLength) {
    return normalized
  }
  return `${normalized.slice(0, maxLength - 1)}...`
}

export function normalizeApiRuntimeStatus(value: string | undefined): ApiRuntimeStatus {
  const normalized = (value ?? "").trim().toLocaleLowerCase("en-US")
  if (normalized === "ok") {
    return "ok"
  }
  if (normalized === "degraded") {
    return "degraded"
  }
  if (normalized === "inactive") {
    return "inactive"
  }
  if (normalized === "missing_key") {
    return "missing_key"
  }
  if (normalized === "disabled") {
    return "disabled"
  }
  return "unknown"
}

export function apiStatusBadgeClass(status: ApiRuntimeStatus): string {
  if (status === "ok") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700"
  }
  if (status === "degraded" || status === "missing_key") {
    return "border-amber-300 bg-amber-50 text-amber-700"
  }
  if (status === "inactive" || status === "disabled") {
    return "border-zinc-300 bg-zinc-50 text-zinc-700"
  }
  return "border-red-300 bg-red-50 text-red-700"
}

export function humanizeApiStatus(status: ApiRuntimeStatus): string {
  if (status === "missing_key") {
    return "missing key"
  }
  return status
}

export function humanizeApiName(name: string): string {
  if (name === "backend") {
    return "Backend API"
  }
  if (name === "azure_translator") {
    return "Azure Translator API"
  }
  if (name === "azure_speech") {
    return "Azure Speech API"
  }
  return name
}

export function finalizedAnalysisText(text: string): string {
  if (!text) {
    return ""
  }

  const hadTrailingWhitespace = /\s$/u.test(text)
  const trimmedRight = text.replace(/\s+$/u, "")
  if (!trimmedRight) {
    return ""
  }

  if (hadTrailingWhitespace) {
    return trimmedRight
  }

  if (/[\p{L}\p{N}]$/u.test(trimmedRight)) {
    return trimmedRight.replace(/[\p{L}\p{N}'’-]+$/u, "").trimEnd()
  }

  return trimmedRight
}

export function addLoadingKey(token: AnalyzedToken): string {
  return `${token.normalized_token || token.surface_token}:${token.classification}`
}

export function normalizeWordKey(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase()
}

export function normalizePhraseKey(value: string): string {
  return normalizeWordKey(value).replace(/\s+/gu, " ").trim()
}

export function normalizeSearchWord(value: string): string {
  return normalizePhraseKey(value)
}

export function isPlayableAudioContentType(contentType: string | null): boolean {
  if (!contentType) {
    return true
  }
  const normalized = contentType.toLocaleLowerCase()
  return (
    normalized.includes("audio/wav")
    || normalized.includes("audio/x-wav")
    || normalized.includes("audio/mpeg")
    || normalized.includes("audio/mp3")
    || normalized.includes("audio/ogg")
    || normalized.includes("audio/webm")
    || normalized.includes("audio/mp4")
    || normalized.includes("audio/aac")
    || normalized.includes("audio/flac")
  )
}

export function isUnsupportedAudioError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false
  }
  const normalized = error.message.toLocaleLowerCase()
  return normalized.includes("no supported source was found")
    || normalized.includes("notsupportederror")
    || normalized.includes("unsupported pronunciation format")
}

export function compactMessage(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/gu, " ").trim()
}

export function normalizeVerificationMessage(message: string | null | undefined): string {
  const normalized = compactMessage(message)
  if (!normalized) {
    return ""
  }
  return normalized.replace(/^verification task failed:\s*/iu, "")
}

export function buildVerificationErrorDetail(payload: {
  provider: string | null | undefined
  status: "flagged" | "error"
  message: string | null | undefined
  composedWordCount?: number | null
  storedSurfaceForm?: string | null
  problem?: string | null
  changeToImplement?: string | null
  suggestedChanges?: {
    lemma_pos_tag?: string | null
    lemma_morphology?: string | null
    surface_pos_tag?: string | null
    surface_morphology?: string | null
    lexeme_translation?: string | null
    surface_translation?: string | null
  } | null
}): VerificationErrorDetail {
  const providerName = payload.provider?.trim() || "gemini"
  const detail = normalizeVerificationMessage(payload.message)
  const suggestedChanges = payload.suggestedChanges
    ? {
      lemmaPosTag: payload.suggestedChanges.lemma_pos_tag ?? undefined,
      lemmaMorphology: payload.suggestedChanges.lemma_morphology ?? undefined,
      surfacePosTag: payload.suggestedChanges.surface_pos_tag ?? undefined,
      surfaceMorphology: payload.suggestedChanges.surface_morphology ?? undefined,
      lexemeTranslation: payload.suggestedChanges.lexeme_translation ?? undefined,
      surfaceTranslation: payload.suggestedChanges.surface_translation ?? undefined,
    }
    : undefined
  const normalizedSurface = normalizeSearchWord(payload.storedSurfaceForm ?? "") || null
  const explicitProblem = compactMessage(payload.problem)
  const explicitChange = compactMessage(payload.changeToImplement)

  if (payload.status === "flagged") {
    const count = payload.composedWordCount ?? 0
    const composedHint = count > 1 ? ` It appears to be treated as a composed word (${count} parts).` : ""
    return {
      provider: providerName,
      status: "flagged",
      problem: explicitProblem || (detail
        ? `Gemini flagged this entry as incorrect: ${detail}.`
        : `Gemini flagged this entry as incorrect.${composedHint}`),
      changeToImplement: explicitChange || "Review lemma/surface form and translation, then update the entry to a valid Danish word form.",
      rawMessage: detail || explicitProblem || "Gemini flagged the entry as incorrect.",
      storedSurfaceForm: normalizedSurface,
      suggestedChanges,
      suggestedChangesPayload: payload.suggestedChanges ?? undefined,
    }
  }

  if (/missing|required|api key|not configured/iu.test(detail)) {
    return {
      provider: providerName,
      status: "error",
      problem: explicitProblem || detail || "Gemini verification could not run because configuration is missing.",
      changeToImplement: explicitChange || "Set the Gemini verification API key in Developer settings or backend env, then retry verification.",
      rawMessage: detail || explicitProblem || "Missing Gemini verification configuration.",
      storedSurfaceForm: normalizedSurface,
      suggestedChanges,
      suggestedChangesPayload: payload.suggestedChanges ?? undefined,
    }
  }

  if (/quota|rate limit|429|too many requests/iu.test(detail)) {
    return {
      provider: providerName,
      status: "error",
      problem: explicitProblem || detail || "Gemini verification request was rate-limited.",
      changeToImplement: explicitChange || "Retry verification after a short delay, or use an API key with higher quota.",
      rawMessage: detail || explicitProblem || "Gemini verification request was rate-limited.",
      storedSurfaceForm: normalizedSurface,
      suggestedChanges,
      suggestedChangesPayload: payload.suggestedChanges ?? undefined,
    }
  }

  return {
    provider: providerName,
    status: "error",
    problem: explicitProblem || detail || "Gemini verification failed unexpectedly.",
    changeToImplement: explicitChange || "Check verification input and retry. If it persists, inspect backend logs for provider errors.",
    rawMessage: detail || explicitProblem || "Gemini verification failed unexpectedly.",
    storedSurfaceForm: normalizedSurface,
    suggestedChanges,
    suggestedChangesPayload: payload.suggestedChanges ?? undefined,
  }
}

export function isShortLetterWord(value: string): boolean {
  const cleaned = value.trim()
  if (!cleaned) {
    return false
  }

  const letters = Array.from(cleaned).filter((character) => /\p{L}/u.test(character)).length
  if (letters === 0 || letters >= 3) {
    return false
  }

  return /^[\p{L}\-'’]+$/u.test(cleaned)
}

export function hasMultipleWords(value: string): boolean {
  return value.split(/\s+/u).filter(Boolean).length >= 2
}

export function preferredPopoverSide(lineTop: number, lineBottom: number): "top" | "bottom" {
  const viewportHeight = typeof window === "undefined" ? 800 : window.innerHeight
  const spaceAbove = lineTop - POPOVER_VIEWPORT_MARGIN_PX
  const spaceBelow = viewportHeight - lineBottom - POPOVER_VIEWPORT_MARGIN_PX
  if (spaceBelow >= POPOVER_ESTIMATED_HEIGHT_PX || spaceBelow >= spaceAbove) {
    return "bottom"
  }
  return "top"
}

export type NumberLabel = "Singular" | "Plural"

export function numberFromMorphology(morphology: string | null): NumberLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Number=Sing(\||$)/u.test(morphology)) {
    return "Singular"
  }
  if (/(^|\|)Number=Plur(\||$)/u.test(morphology)) {
    return "Plural"
  }
  return null
}

export type GenderLabel = "Common" | "Neuter" | "Masculine" | "Feminine"

export function genderFromMorphology(morphology: string | null): GenderLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Gender=Com(\||$)/u.test(morphology)) {
    return "Common"
  }
  if (/(^|\|)Gender=Neut(\||$)/u.test(morphology)) {
    return "Neuter"
  }
  if (/(^|\|)Gender=Masc(\||$)/u.test(morphology)) {
    return "Masculine"
  }
  if (/(^|\|)Gender=Fem(\||$)/u.test(morphology)) {
    return "Feminine"
  }
  return null
}

export type DeterminerWordType = "n-word" | "t-word"

export function determinerWordTypeFromMorphology(morphology: string | null): DeterminerWordType | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Gender=Neut(\||$)/u.test(morphology)) {
    return "t-word"
  }
  if (/(^|\|)Gender=(Com|Masc|Fem)(\||$)/u.test(morphology)) {
    return "n-word"
  }
  return null
}

export type PersonLabel = "1st person" | "2nd person" | "3rd person"

export function personFromMorphology(morphology: string | null): PersonLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Person=1(\||$)/u.test(morphology)) {
    return "1st person"
  }
  if (/(^|\|)Person=2(\||$)/u.test(morphology)) {
    return "2nd person"
  }
  if (/(^|\|)Person=3(\||$)/u.test(morphology)) {
    return "3rd person"
  }
  return null
}

export type DegreeLabel = "Positive" | "Comparative" | "Superlative"

export function degreeFromMorphology(morphology: string | null): DegreeLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Degree=Pos(\||$)/u.test(morphology)) {
    return "Positive"
  }
  if (/(^|\|)Degree=Cmp(\||$)/u.test(morphology)) {
    return "Comparative"
  }
  if (/(^|\|)Degree=Sup(\||$)/u.test(morphology)) {
    return "Superlative"
  }
  return null
}

export type VerbFormLabel = "Infinitive" | "Present" | "Past (preterite)" | "Past participle"

export function verbFormFromMorphology(morphology: string | null): VerbFormLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)VerbForm=Part(\||$)/u.test(morphology)) {
    return "Past participle"
  }
  if (/(^|\|)VerbForm=Inf(\||$)/u.test(morphology)) {
    return "Infinitive"
  }
  if (/(^|\|)Tense=Past(\||$)/u.test(morphology)) {
    return "Past (preterite)"
  }
  if (/(^|\|)Tense=Pres(\||$)/u.test(morphology)) {
    return "Present"
  }
  return null
}

export type DefinitenessLabel = "Indefinite" | "Definite"

export function definitenessFromMorphology(morphology: string | null): DefinitenessLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Definite=Ind(\||$)/u.test(morphology)) {
    return "Indefinite"
  }
  if (/(^|\|)Definite=Def(\||$)/u.test(morphology)) {
    return "Definite"
  }
  return null
}

export type CaseLabel = "Genitive"

export function caseFromMorphology(morphology: string | null): CaseLabel | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Case=Gen(\||$)/u.test(morphology)) {
    return "Genitive"
  }
  return null
}

export function posBadgeClass(posTag: string | null): string {
  if (!posTag) {
    return ""
  }

  const colorByPos: Record<string, string> = {
    ADJ: "bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-200 border-transparent",
    ADP: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200 border-transparent",
    ADV: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200 border-transparent",
    AUX: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200 border-transparent",
    CCONJ: "bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-200 border-transparent",
    DET: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 border-transparent",
    INTJ: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200 border-transparent",
    NOUN: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 border-transparent",
    NUM: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200 border-transparent",
    PART: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200 border-transparent",
    PRON: "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200 border-transparent",
    PROPN: "bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/40 dark:text-fuchsia-200 border-transparent",
    PUNCT: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-transparent",
    SCONJ: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200 border-transparent",
    SYM: "bg-stone-100 text-stone-800 dark:bg-stone-800 dark:text-stone-200 border-transparent",
    VERB: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200 border-transparent",
    X: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200 border-transparent",
  }

  return colorByPos[posTag] ?? "bg-muted text-muted-foreground border-transparent"
}

export function secondaryTagsForPos(posTag: string | null, morphology: string | null): string[] {
  const tags: string[] = []
  if (posTag === "VERB" || posTag === "AUX") {
    const form = verbFormFromMorphology(morphology)
    if (form) {
      tags.push(form)
    }
  }
  if (posTag === "NOUN") {
    const wordType = determinerWordTypeFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    const definiteness = definitenessFromMorphology(morphology)
    const caseLabel = caseFromMorphology(morphology)
    if (wordType) {
      tags.push(wordType)
    }
    if (number) {
      tags.push(number)
    }
    if (definiteness) {
      tags.push(definiteness)
    }
    if (caseLabel) {
      tags.push(caseLabel)
    }
  }
  if (posTag === "DET") {
    const gender = determinerWordTypeFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (gender) {
      tags.push(gender)
    }
    if (number) {
      tags.push(number)
    }
  }
  if (posTag === "ADJ") {
    const gender = genderFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (gender) {
      tags.push(gender)
    }
    if (number) {
      tags.push(number)
    }
  }
  if (posTag === "PRON") {
    const person = personFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (person) {
      tags.push(person)
    }
    if (number) {
      tags.push(number)
    }
  }
  if (posTag === "ADV") {
    const degree = degreeFromMorphology(morphology)
    if (degree) {
      tags.push(degree)
    }
  }
  return tags
}

export function isLowConfidencePosTag(posTag: string | null): boolean {
  return !posTag || posTag === "X"
}

export const GRAM_POS_LABELS: Record<string, string> = {
  sb: "Noun",
  vb: "Verb",
  adj: "Adjective",
  adv: "Adverb",
  pron: "Pronoun",
  "præp": "Preposition",
  konj: "Conjunction",
  art: "Article",
  prop: "Proper noun",
  talord: "Numeral",
  "udråbsord": "Interjection",
  lydord: "Onomatopoeia",
  fork: "Abbreviation",
  flerord: "Multiword",
  iflerord: "Multiword part",
  "præfiks": "Prefix",
  suffiks: "Suffix",
  romertal: "Roman numeral",
  "infmærke": "Infinitive marker",
}

export const GRAM_FEATURE_LABELS: Record<string, string> = {
  fk: "n-word",
  itk: "t-word",
  sg: "Singular",
  pl: "Plural",
  ubest: "Indefinite",
  best: "Definite",
  gen: "Genitive",
  sms: "Compound form",
  "præs": "Present",
  "præt": "Past",
  inf: "Infinitive",
  imp: "Imperative",
  akt: "Active",
  pass: "Passive",
  kompar: "Comparative",
  superl: "Superlative",
  adv: "Adverbial",
}

export type CorSearchBadge = {
  label: string
  tone: "primary" | "secondary"
}

export const COR_SECONDARY_BADGE_CLASS_BY_LABEL: Record<string, string> = {
  "n-word": "bg-emerald-50 text-emerald-900 border-emerald-400 dark:bg-emerald-950/30 dark:text-emerald-200 dark:border-emerald-500",
  "t-word": "bg-teal-50 text-teal-900 border-teal-400 dark:bg-teal-950/30 dark:text-teal-200 dark:border-teal-500",
  Singular: "bg-sky-50 text-sky-900 border-sky-400 dark:bg-sky-950/30 dark:text-sky-200 dark:border-sky-500",
  Plural: "bg-indigo-50 text-indigo-900 border-indigo-400 dark:bg-indigo-950/30 dark:text-indigo-200 dark:border-indigo-500",
  Indefinite: "bg-amber-50 text-amber-900 border-amber-400 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-500",
  Definite: "bg-yellow-50 text-yellow-900 border-yellow-400 dark:bg-yellow-950/30 dark:text-yellow-200 dark:border-yellow-500",
  Genitive: "bg-orange-50 text-orange-900 border-orange-400 dark:bg-orange-950/30 dark:text-orange-200 dark:border-orange-500",
  "Compound form": "bg-slate-50 text-slate-900 border-slate-400 dark:bg-slate-900/40 dark:text-slate-200 dark:border-slate-500",
  Present: "bg-cyan-50 text-cyan-900 border-cyan-400 dark:bg-cyan-950/30 dark:text-cyan-200 dark:border-cyan-500",
  Past: "bg-violet-50 text-violet-900 border-violet-400 dark:bg-violet-950/30 dark:text-violet-200 dark:border-violet-500",
  Infinitive: "bg-lime-50 text-lime-900 border-lime-400 dark:bg-lime-950/30 dark:text-lime-200 dark:border-lime-500",
  Imperative: "bg-red-50 text-red-900 border-red-400 dark:bg-red-950/30 dark:text-red-200 dark:border-red-500",
  Active: "bg-blue-50 text-blue-900 border-blue-400 dark:bg-blue-950/30 dark:text-blue-200 dark:border-blue-500",
  Passive: "bg-fuchsia-50 text-fuchsia-900 border-fuchsia-400 dark:bg-fuchsia-950/30 dark:text-fuchsia-200 dark:border-fuchsia-500",
  Comparative: "bg-pink-50 text-pink-900 border-pink-400 dark:bg-pink-950/30 dark:text-pink-200 dark:border-pink-500",
  Superlative: "bg-rose-50 text-rose-900 border-rose-400 dark:bg-rose-950/30 dark:text-rose-200 dark:border-rose-500",
  Adverbial: "bg-stone-50 text-stone-900 border-stone-400 dark:bg-stone-900/40 dark:text-stone-200 dark:border-stone-500",
  "Perfect participle": "bg-purple-50 text-purple-900 border-purple-400 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-500",
}

export function corSecondaryBadgeClass(label: string): string {
  return COR_SECONDARY_BADGE_CLASS_BY_LABEL[label] ?? "bg-muted text-muted-foreground border-muted-foreground/60"
}

export const UD_POS_PRIMARY_LABELS: Record<string, string> = {
  ADJ: "Adjective",
  ADP: "Preposition",
  ADV: "Adverb",
  AUX: "Auxiliary",
  CCONJ: "Conjunction",
  DET: "Determiner",
  INTJ: "Interjection",
  NOUN: "Noun",
  NUM: "Numeral",
  PART: "Particle",
  PRON: "Pronoun",
  PROPN: "Proper noun",
  PUNCT: "Punctuation",
  SCONJ: "Subordinating conjunction",
  SYM: "Symbol",
  VERB: "Verb",
  X: "Other",
}

export function primaryPosLabel(posTag: string | null): string | null {
  if (!posTag) {
    return null
  }
  return UD_POS_PRIMARY_LABELS[posTag] ?? posTag
}

export function badgesFromGramRaw(gramRaw: string): CorSearchBadge[] {
  const normalized = gramRaw.trim().toLocaleLowerCase("da-DK")
  if (!normalized) {
    return []
  }
  const grams = normalized.split("|").map((item) => item.trim()).filter(Boolean)
  const labels: CorSearchBadge[] = []

  for (const gram of grams) {
    const rawChunks = gram.split(".").filter(Boolean)
    const chunks: string[] = []
    for (let index = 0; index < rawChunks.length; index += 1) {
      const current = rawChunks[index]
      const next = rawChunks[index + 1]
      if (current === "perf" && next === "part") {
        chunks.push("perf.part")
        index += 1
        continue
      }
      chunks.push(current)
    }

    for (let index = 0; index < chunks.length; index += 1) {
      const chunk = chunks[index]
      if (index === 0) {
        const posLabel = GRAM_POS_LABELS[chunk]
        if (posLabel) {
          labels.push({ label: posLabel, tone: "primary" })
        }
        continue
      }
      if (chunk === "perf.part") {
        labels.push({ label: "Perfect participle", tone: "secondary" })
        continue
      }
      const feature = GRAM_FEATURE_LABELS[chunk]
      if (feature) {
        labels.push({ label: feature, tone: "secondary" })
      }
    }
  }

  return labels.filter((badge, index, array) => array.findIndex((candidate) => candidate.label === badge.label) === index)
}

export function lemmaDisplayForVariant(variant: CORSearchVariant): string | null {
  const lemma = variant.lemma.trim()
  if (!lemma) {
    return null
  }
  if ((variant.pos_tag ?? "").toUpperCase() === "VERB") {
    return `at ${lemma}`
  }
  return lemma
}

export function lemmaTranslationForVariant(variant: CORSearchVariant): string | null {
  const value = variant.lemma_translation?.trim()
  return value ? value : null
}

export function glossDisplayForVariant(variant: CORSearchVariant): string | null {
  const gloss = variant.gloss?.trim()
  if (!gloss) {
    return null
  }
  const translation = variant.gloss_translation?.trim()
  if (!translation) {
    return gloss
  }
  return `${gloss} (${translation})`
}

export function lemmaDisplayForSavedForm(form: {
  form: string
  lemma?: string | null
  pos_tag?: string | null
}): string | null {
  const lemma = form.lemma?.trim()
  if (!lemma) {
    return null
  }
  if ((form.pos_tag ?? "").toUpperCase() === "VERB") {
    return `at ${lemma}`
  }
  return lemma
}

export function glossDisplayForSavedForm(form: {
  gloss?: string | null
  gloss_translation?: string | null
}): string | null {
  const gloss = form.gloss?.trim()
  if (!gloss) {
    return null
  }
  const translation = form.gloss_translation?.trim()
  if (!translation) {
    return gloss
  }
  return `${gloss} (${translation})`
}

export function badgesForSavedForm(form: {
  pos_tag?: string | null
  morphology?: string | null
  gram_raw?: string | null
}): CorSearchBadge[] {
  if (form.gram_raw?.trim()) {
    return badgesFromGramRaw(form.gram_raw)
  }
  return [
    ...(form.pos_tag ? [{ label: primaryPosLabel(form.pos_tag) ?? form.pos_tag, tone: "primary" as const }] : []),
    ...secondaryTagsForPos(form.pos_tag ?? null, form.morphology ?? null).map((tag) => ({
      label: tag,
      tone: "secondary" as const,
    })),
  ]
}


export function translationKeysForToken(token: Pick<AnalyzedToken, "surface_token" | "normalized_token">): string[] {
  const keys = [
    token.normalized_token,
    token.surface_token,
  ]
    .filter((value): value is string => Boolean(value && value.trim()))
    .map((value) => normalizeWordKey(value))

  return [...new Set(keys)]
}
