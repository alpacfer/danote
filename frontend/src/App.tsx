import { useEffect, useMemo, useRef, useState } from "react"
import { Bell, BookOpen, Eye, Info, Moon, NotebookPen, Plus, RefreshCw, Save, Settings, Sun, Volume2 } from "lucide-react"
import { useTheme } from "next-themes"

import { Badge } from "@/components/ui/badge"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverAnchor, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { NotesEditor } from "@/components/notes-editor"
import { mapAnalyzedTokensToHighlights } from "@/lib/token-highlights"
import { toast } from "sonner"

type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
type ApiRuntimeStatus = "ok" | "degraded" | "inactive" | "missing_key" | "disabled" | "unknown"
type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
type AppSection = "playground" | "notes" | "wordbank" | "sentencebank" | "developer"
type TokenAction = "add_as_new"

type WordActionSuggestion = {
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

type AnalyzedToken = {
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

type AddWordResponse = {
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

type VerifyWordResponse = {
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

type GeneratePronunciationResponse = {
  status: "generated" | "unavailable" | "skipped"
  stored_lemma: string
  stored_surface_form: string | null
  pronunciation_form: string | null
}

type ApplyVerificationChangesResponse = {
  status: "applied" | "skipped"
  stored_lemma: string
  stored_surface_form: string | null
  applied_fields: string[]
}

type WordbankLemma = {
  lemma: string
  display_lemma?: string | null
  english_translation: string | null
  variation_count: number
}

type LemmaListResponse = {
  items: WordbankLemma[]
}

type WordbankSearchItem = {
  lemma: string
  display_lemma: string
  english_translation: string | null
  variation_count: number
  match_surface?: string | null
}

type WordbankSearchResponse = {
  items: WordbankSearchItem[]
}

type LemmaDetailsResponse = {
  lemma: string
  english_translation: string | null
  pos_tag: string | null
  morphology: string | null
  surface_forms: Array<{
    form: string
    english_translation: string | null
    pos_tag: string | null
    morphology: string | null
    has_pronunciation?: boolean
  }>
}

type ResetDatabaseResponse = {
  status: "reset"
  message: string
}

type GenerateTranslationResponse = {
  status: "generated" | "unavailable"
  source_word: string
  lemma: string
  english_translation: string | null
}

type ResolveQueryResponse = {
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

type GeneratePhraseTranslationResponse = {
  status: "generated" | "cached" | "unavailable"
  source_text: string
  english_translation: string | null
}

type SentencebankSentence = {
  id: number
  source_text: string
  english_translation: string | null
  created_at: string
}

type SentenceListResponse = {
  items: SentencebankSentence[]
}

type AddSentenceResponse = {
  status: "inserted" | "exists"
  source_text: string
  english_translation: string | null
  message: string
}

type HealthApiStatusEntry = {
  status?: string
  active?: boolean
  configured?: boolean
  message?: string | null
}

type HealthPayload = {
  status?: string
  service?: string
  components?: Record<string, string>
  apis?: Record<string, HealthApiStatusEntry>
}

type DeveloperApiKeysUpdateResponse = {
  status: string
  message: string
  configured: Record<string, boolean>
}

type TokenFeedbackPayload = {
  raw_token: string
  predicted_status: string
  suggestions_shown: string[]
  user_action: TokenAction
  chosen_value?: string
  source?: "playground" | "search"
}

type SearchFeedbackContext = {
  rawToken: string
  predictedStatus: TokenClassification
  suggestionsShown: string[]
}

type HighlightPopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  tokenIndex: number | null
}

type PhrasePopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  selectedText: string
}

type DiscoveredTokenMetadata = {
  pos_tag: string
  morphology: string | null
  lemma: string | null
  word_actions?: WordActionSuggestion[]
}

type DiscoveredTokenMemory = {
  latest: DiscoveredTokenMetadata
  byPos: Record<string, DiscoveredTokenMetadata>
}

type SaveDialogMode = "initial" | "create_new"

type SavedNote = {
  id: string
  name: string
  text: string
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  savedAt: string
}

type AppNotification = {
  id: string
  message: string
  createdAt: string
  read: boolean
}

type VerificationErrorDetail = {
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

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
const ANALYZE_DEBOUNCE_MS = 450
const SEARCH_RESOLVE_DEBOUNCE_MS = 220
const POPOVER_ENRICH_CACHE_TTL_MS = 60_000
const PHRASE_TRANSLATION_DELAY_MS = 1000
const NLP_MODEL_OPTIONS = [
  "da_dacy_small_trf-0.2.0",
  "da_dacy_medium_trf-0.2.0",
  "da_dacy_large_trf-0.2.0",
] as const
const POPOVER_VIEWPORT_MARGIN_PX = 12
const POPOVER_ESTIMATED_HEIGHT_PX = 280
const PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS = "max-w-[42ch]"
const SAVED_NOTES_STORAGE_KEY = "danote.saved-notes.v1"
const NOTE_AUTOSAVE_DEBOUNCE_MS = 900

type NlpModelOption = (typeof NLP_MODEL_OPTIONS)[number]

function loadSavedNotes(): SavedNote[] {
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

function persistSavedNotes(notes: SavedNote[]) {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.setItem(SAVED_NOTES_STORAGE_KEY, JSON.stringify(notes))
}

function createSavedNoteId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `note-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function createNotificationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `notification-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function formatSavedNoteTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

function previewText(value: string, maxLength = 180): string {
  const normalized = value.replace(/\s+/gu, " ").trim()
  if (!normalized) {
    return "No text saved."
  }
  if (normalized.length <= maxLength) {
    return normalized
  }
  return `${normalized.slice(0, maxLength - 1)}...`
}

function normalizeApiRuntimeStatus(value: string | undefined): ApiRuntimeStatus {
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

function apiStatusBadgeClass(status: ApiRuntimeStatus): string {
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

function humanizeApiStatus(status: ApiRuntimeStatus): string {
  if (status === "missing_key") {
    return "missing key"
  }
  return status
}

function humanizeApiName(name: string): string {
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

async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // Fall through to default message.
  }
  return fallback
}

function finalizedAnalysisText(text: string): string {
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

function addLoadingKey(token: AnalyzedToken): string {
  return `${token.normalized_token || token.surface_token}:${token.classification}`
}

function normalizeWordKey(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase()
}

function normalizePhraseKey(value: string): string {
  return normalizeWordKey(value).replace(/\s+/gu, " ").trim()
}

function normalizeSearchWord(value: string): string {
  return normalizePhraseKey(value)
}

function isPlayableAudioContentType(contentType: string | null): boolean {
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

function isUnsupportedAudioError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false
  }
  const normalized = error.message.toLocaleLowerCase()
  return normalized.includes("no supported source was found")
    || normalized.includes("notsupportederror")
    || normalized.includes("unsupported pronunciation format")
}

function compactMessage(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/gu, " ").trim()
}

function normalizeVerificationMessage(message: string | null | undefined): string {
  const normalized = compactMessage(message)
  if (!normalized) {
    return ""
  }
  return normalized.replace(/^verification task failed:\s*/iu, "")
}

function buildVerificationErrorDetail(payload: {
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

function isShortLetterWord(value: string): boolean {
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

function hasMultipleWords(value: string): boolean {
  return value.split(/\s+/u).filter(Boolean).length >= 2
}

function preferredPopoverSide(lineTop: number, lineBottom: number): "top" | "bottom" {
  const viewportHeight = typeof window === "undefined" ? 800 : window.innerHeight
  const spaceAbove = lineTop - POPOVER_VIEWPORT_MARGIN_PX
  const spaceBelow = viewportHeight - lineBottom - POPOVER_VIEWPORT_MARGIN_PX
  if (spaceBelow >= POPOVER_ESTIMATED_HEIGHT_PX || spaceBelow >= spaceAbove) {
    return "bottom"
  }
  return "top"
}

type NumberLabel = "Singular" | "Plural"

function numberFromMorphology(morphology: string | null): NumberLabel | null {
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

type GenderLabel = "Common" | "Neuter" | "Masculine" | "Feminine"

function genderFromMorphology(morphology: string | null): GenderLabel | null {
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

type DeterminerWordType = "n-word" | "t-word"

function determinerWordTypeFromMorphology(morphology: string | null): DeterminerWordType | null {
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

type PersonLabel = "1st person" | "2nd person" | "3rd person"

function personFromMorphology(morphology: string | null): PersonLabel | null {
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

type DegreeLabel = "Positive" | "Comparative" | "Superlative"

function degreeFromMorphology(morphology: string | null): DegreeLabel | null {
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

type VerbFormLabel = "Infinitive" | "Present" | "Past (preterite)" | "Past participle"

function verbFormFromMorphology(morphology: string | null): VerbFormLabel | null {
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

function posBadgeClass(posTag: string | null): string {
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

function secondaryTagsForPos(posTag: string | null, morphology: string | null): string[] {
  const tags: string[] = []
  if (posTag === "VERB" || posTag === "AUX") {
    const form = verbFormFromMorphology(morphology)
    if (form) {
      tags.push(form)
    }
  }
  if (posTag === "NOUN") {
    const number = numberFromMorphology(morphology)
    if (number) {
      tags.push(number)
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

function isLowConfidencePosTag(posTag: string | null): boolean {
  return !posTag || posTag === "X"
}


function translationKeysForToken(token: Pick<AnalyzedToken, "surface_token" | "normalized_token">): string[] {
  const keys = [
    token.normalized_token,
    token.surface_token,
  ]
    .filter((value): value is string => Boolean(value && value.trim()))
    .map((value) => normalizeWordKey(value))

  return [...new Set(keys)]
}

type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  savedNotes: SavedNote[]
  onSelectPlayground: () => void
  onSelectNotes: () => void
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenSavedNote: (noteId: string) => void
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ) => Promise<string | null>
}

function ThemeToggleButton() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === "dark"

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="self-start"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => {
        setTheme(isDark ? "light" : "dark")
      }}
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  )
}

type AppBreadcrumbProps = {
  activeSection: AppSection
  selectedLemma: string | null
  activeNoteName: string | null
  onSelectWordbank: () => void
}

function AppBreadcrumb({
  activeSection,
  selectedLemma,
  activeNoteName,
  onSelectWordbank,
}: AppBreadcrumbProps) {
  if (activeSection === "playground") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl font-semibold">
          <BreadcrumbItem>
            <BreadcrumbPage>{activeNoteName?.trim() || "Playground"}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "developer") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl font-semibold">
          <BreadcrumbItem>
            <BreadcrumbPage>Developer</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "notes") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl font-semibold">
          <BreadcrumbItem>
            <BreadcrumbPage>Notes</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "sentencebank") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl font-semibold">
          <BreadcrumbItem>
            <BreadcrumbPage>Sentencebank</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  return (
    <Breadcrumb>
      <BreadcrumbList className="text-2xl font-semibold">
        <BreadcrumbItem>
          {selectedLemma ? (
            <BreadcrumbLink asChild>
              <button type="button" className="font-semibold" onClick={onSelectWordbank}>
                Wordbank
              </button>
            </BreadcrumbLink>
          ) : (
            <BreadcrumbPage>Wordbank</BreadcrumbPage>
          )}
        </BreadcrumbItem>
        {selectedLemma && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{selectedLemma}</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

function AppSidebar({
  activeSection,
  lemmas,
  savedNotes,
  onSelectPlayground,
  onSelectNotes,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
  onOpenSavedNote,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const resolveQueryCacheRef = useRef<Map<string, ResolveQueryResponse>>(new Map())
  const wordbankSearchCacheRef = useRef<Map<string, Array<{ lemma: WordbankLemma; matchSurface: string | null }>>>(new Map())
  const [searchApiMatches, setSearchApiMatches] = useState<Array<{ lemma: WordbankLemma; matchSurface: string | null }>>([])
  const [resolvedQueryCandidate, setResolvedQueryCandidate] = useState<{
    query: string
    surface: string
    lemma: string | null
    classification: TokenClassification
    querySurface: string
    queryLemma: string | null
    queryPosTag: string | null
    queryMorphology: string | null
    daToEnTranslation: string | null
    enToDaTranslation: string | null
    enToDaLemma: string | null
    enToDaPosTag: string | null
    enToDaMorphology: string | null
    queryLanguage: "en" | "da" | "ambiguous" | null
    queryLanguageConfidence: number | null
    matchedLemma: WordbankLemma | null
    wordActions: WordActionSuggestion[]
  } | null>(null)
  const trimmedQuery = normalizeSearchWord(searchQuery)
  const normalizedQuery = trimmedQuery
  const matchingLemmas = useMemo(() => {
    if (!normalizedQuery) {
      return []
    }
    return lemmas
      .filter((lemma) => {
        const lemmaValue = lemma.lemma.trim().toLocaleLowerCase("da-DK")
        const translationValue = lemma.english_translation?.trim().toLocaleLowerCase("da-DK") ?? ""
        return lemmaValue.includes(normalizedQuery) || translationValue.includes(normalizedQuery)
      })
      .slice(0, 8)
  }, [lemmas, normalizedQuery])
  const matchingNotes = useMemo(() => {
    if (!normalizedQuery) {
      return []
    }
    return savedNotes
      .filter((note) => {
        const name = note.name.trim().toLocaleLowerCase("da-DK")
        const text = note.text.trim().toLocaleLowerCase("da-DK")
        return name.includes(normalizedQuery) || text.includes(normalizedQuery)
      })
      .slice(0, 8)
  }, [normalizedQuery, savedNotes])
  const activeResolvedCandidate = useMemo(() => {
    if (!resolvedQueryCandidate || resolvedQueryCandidate.query !== normalizedQuery) {
      return null
    }
    return resolvedQueryCandidate
  }, [normalizedQuery, resolvedQueryCandidate])

  useEffect(() => {
    let cancelled = false
    const commitSearchMatches = (nextMatches: Array<{ lemma: WordbankLemma; matchSurface: string | null }>) => {
      window.setTimeout(() => {
        if (!cancelled) {
          setSearchApiMatches(nextMatches)
        }
      }, 0)
    }

    if (!normalizedQuery) {
      commitSearchMatches([])
      return () => {
        cancelled = true
      }
    }

    const cached = wordbankSearchCacheRef.current.get(normalizedQuery)
    if (cached) {
      commitSearchMatches(cached)
      return () => {
        cancelled = true
      }
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const response = await fetch(
            `${BACKEND_URL}/api/wordbank/search?query=${encodeURIComponent(trimmedQuery)}&limit=8`,
            { signal: controller.signal },
          )
          if (!response.ok) {
            if (!cancelled) {
              commitSearchMatches([])
            }
            return
          }
          const payload = (await response.json()) as WordbankSearchResponse
          if (cancelled) {
            return
          }
          const mapped = (payload.items ?? []).map((item) => ({
            lemma: {
              lemma: item.lemma,
              display_lemma: item.display_lemma,
              english_translation: item.english_translation,
              variation_count: item.variation_count,
            },
            matchSurface: item.match_surface ?? null,
          }))
          wordbankSearchCacheRef.current.set(normalizedQuery, mapped)
          commitSearchMatches(mapped)
        } catch {
          if (!cancelled) {
            commitSearchMatches([])
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [normalizedQuery, trimmedQuery])

  const wordbankResults = useMemo(() => {
    const variationMatch = activeResolvedCandidate?.matchedLemma
      ? {
        lemma: activeResolvedCandidate.matchedLemma,
        surface: activeResolvedCandidate.surface,
      }
      : null
    const directMatches = (searchApiMatches.length > 0 ? searchApiMatches : matchingLemmas.map((lemma) => ({
      lemma,
      matchSurface: null as string | null,
    }))).map((item) => ({ lemma: item.lemma, matchSurface: item.matchSurface ?? null }))

    if (!variationMatch) {
      return directMatches
    }

    const hasLemma = directMatches.some((item) => item.lemma.lemma === variationMatch.lemma.lemma)
    if (hasLemma) {
      return directMatches
    }

    return [{ lemma: variationMatch.lemma, matchSurface: variationMatch.surface }, ...directMatches]
  }, [activeResolvedCandidate, matchingLemmas, searchApiMatches])
  const hasWordbankResults = wordbankResults.length > 0
  const searchWordActions = useMemo(() => {
    if (!activeResolvedCandidate) {
      return []
    }
    return activeResolvedCandidate.wordActions.filter((action) => action.action_type !== "open_wordbank")
  }, [activeResolvedCandidate])
  const newWordOptions = useMemo(() => searchWordActions.filter((action) => action.action_type === "add_as_new"), [searchWordActions])
  const addVariationResult = useMemo(() => searchWordActions.find((action) => action.action_type === "add_variation") ?? null, [searchWordActions])
  const hasWordbankSectionResults = hasWordbankResults || newWordOptions.length > 0
  const hasWordbankActions = newWordOptions.length > 0 || Boolean(addVariationResult)
  const hasNoteResults = matchingNotes.length > 0
  const pageItems = useMemo(
    () => [
      {
        key: "page-playground",
        label: "Playground",
        shortcut: "Alt+P",
        icon: NotebookPen,
        onSelect: onSelectPlayground,
      },
      {
        key: "page-notes",
        label: "Notes",
        shortcut: "Alt+N",
        icon: BookOpen,
        onSelect: onSelectNotes,
      },
      {
        key: "page-wordbank",
        label: "Wordbank",
        shortcut: "Alt+W",
        icon: BookOpen,
        onSelect: onSelectWordbank,
      },
      {
        key: "page-sentencebank",
        label: "Sentencebank",
        shortcut: "Alt+S",
        icon: BookOpen,
        onSelect: onSelectSentencebank,
      },
      {
        key: "page-developer",
        label: "Developer",
        shortcut: "Alt+D",
        icon: Settings,
        onSelect: onSelectDeveloper,
      },
    ],
    [onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectSentencebank, onSelectWordbank],
  )
  const matchingPageItems = useMemo(() => {
    if (!normalizedQuery) {
      return pageItems
    }
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [normalizedQuery, pageItems])
  const hasPageResults = matchingPageItems.length > 0
  const hasAnyResults = hasWordbankSectionResults || hasNoteResults || hasPageResults

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const key = event.key.toLowerCase()
      const shouldOpenSearch = (event.metaKey || event.ctrlKey) && key === "k"
      if (shouldOpenSearch) {
        event.preventDefault()
        setIsSearchOpen((current) => !current)
        return
      }

      const target = event.target as HTMLElement | null
      const isTypingTarget = Boolean(
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable),
      )
      if (isTypingTarget || !event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
        return
      }

      if (key === "p") {
        event.preventDefault()
        onSelectPlayground()
        return
      }
      if (key === "n") {
        event.preventDefault()
        onSelectNotes()
        return
      }
      if (key === "w") {
        event.preventDefault()
        onSelectWordbank()
        return
      }
      if (key === "s") {
        event.preventDefault()
        onSelectSentencebank()
        return
      }
      if (key === "d") {
        event.preventDefault()
        onSelectDeveloper()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectSentencebank, onSelectWordbank])

  useEffect(() => {
    if (!normalizedQuery || /\s/u.test(normalizedQuery) || isShortLetterWord(normalizedQuery)) {
      return
    }

    const alreadyDirectMatch = matchingLemmas.some(
      (lemma) => lemma.lemma.trim().toLocaleLowerCase("da-DK") === normalizedQuery,
    )
    if (alreadyDirectMatch) {
      return
    }

    const cachedPayload = resolveQueryCacheRef.current.get(normalizedQuery)
    if (cachedPayload) {
      const matchedLemma = cachedPayload.matched_lemma_summary
        ? lemmas.find(
          (lemma) =>
            lemma.lemma.trim().toLocaleLowerCase("da-DK") ===
            cachedPayload.matched_lemma_summary?.lemma.trim().toLocaleLowerCase("da-DK"),
        ) ?? {
          lemma: cachedPayload.matched_lemma_summary.lemma,
          english_translation: cachedPayload.matched_lemma_summary.english_translation,
          variation_count: cachedPayload.matched_lemma_summary.variation_count,
        }
        : null

      setResolvedQueryCandidate({
        query: normalizedQuery,
        surface: cachedPayload.resolved_surface,
        lemma: cachedPayload.resolved_lemma,
        classification: cachedPayload.classification,
        querySurface: cachedPayload.query_surface,
        queryLemma: cachedPayload.query_lemma,
        queryPosTag: cachedPayload.query_pos_tag,
        queryMorphology: cachedPayload.query_morphology,
        daToEnTranslation: cachedPayload.da_to_en_translation,
        enToDaTranslation: cachedPayload.en_to_da_translation,
        enToDaLemma: cachedPayload.en_to_da_lemma,
        enToDaPosTag: cachedPayload.en_to_da_pos_tag,
        enToDaMorphology: cachedPayload.en_to_da_morphology,
        queryLanguage: cachedPayload.query_language,
        queryLanguageConfidence: cachedPayload.query_language_confidence,
        matchedLemma,
        wordActions: cachedPayload.word_actions ?? [],
      })
      return
    }

    const controller = new AbortController()
    let cancelled = false
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const response = await fetch(`${BACKEND_URL}/api/wordbank/resolve-query`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              query_text: trimmedQuery,
            }),
            signal: controller.signal,
          })
          if (!response.ok) {
            setResolvedQueryCandidate((current) => (current?.query === normalizedQuery ? null : current))
            return
          }

          const payload = (await response.json()) as ResolveQueryResponse
          if (cancelled) {
            return
          }
          resolveQueryCacheRef.current.set(normalizedQuery, payload)

          const matchedLemma = payload.matched_lemma_summary
            ? lemmas.find(
              (lemma) =>
                lemma.lemma.trim().toLocaleLowerCase("da-DK") ===
                payload.matched_lemma_summary?.lemma.trim().toLocaleLowerCase("da-DK"),
            ) ?? {
              lemma: payload.matched_lemma_summary.lemma,
              english_translation: payload.matched_lemma_summary.english_translation,
              variation_count: payload.matched_lemma_summary.variation_count,
            }
            : null

          setResolvedQueryCandidate({
            query: normalizedQuery,
            surface: payload.resolved_surface,
            lemma: payload.resolved_lemma,
            classification: payload.classification,
            querySurface: payload.query_surface,
            queryLemma: payload.query_lemma,
            queryPosTag: payload.query_pos_tag,
            queryMorphology: payload.query_morphology,
            daToEnTranslation: payload.da_to_en_translation,
            enToDaTranslation: payload.en_to_da_translation,
            enToDaLemma: payload.en_to_da_lemma,
            enToDaPosTag: payload.en_to_da_pos_tag,
            enToDaMorphology: payload.en_to_da_morphology,
            queryLanguage: payload.query_language,
            queryLanguageConfidence: payload.query_language_confidence,
            matchedLemma,
            wordActions: payload.word_actions ?? [],
          })
        } catch {
          if (!cancelled) {
            setResolvedQueryCandidate((current) => (current?.query === normalizedQuery ? null : current))
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [lemmas, matchingLemmas, normalizedQuery, trimmedQuery])

  useEffect(() => {
    if (isSearchOpen) {
      return
    }
    const clearTimeoutId = window.setTimeout(() => {
      setSearchQuery("")
    }, 220)
    return () => {
      window.clearTimeout(clearTimeoutId)
    }
  }, [isSearchOpen])

  return (
    <Sidebar variant="inset">
      <SidebarHeader className="gap-2">
        <p className="px-2 text-sm font-semibold">Danote</p>
        <Button
          type="button"
          variant="outline"
          className="justify-between"
          onClick={() => setIsSearchOpen(true)}
        >
          Search...
          <span className="text-muted-foreground text-[10px] uppercase">Cmd/Ctrl+K</span>
        </Button>
        <CommandDialog
          open={isSearchOpen}
          onOpenChange={(open) => {
            setIsSearchOpen(open)
          }}
          title="Search wordbank and notes"
          description="Search saved words, variations, translations, and notes."
        >
          <CommandInput
            placeholder="Search words and notes..."
            value={searchQuery}
            onValueChange={(value) => setSearchQuery(normalizeSearchWord(value))}
            aria-label="command search"
          />
          <CommandList>
            {normalizedQuery && !hasAnyResults ? <CommandEmpty>No results found.</CommandEmpty> : null}
            {hasWordbankSectionResults ? (
              <CommandGroup heading="Wordbank">
                {wordbankResults.map(({ lemma, matchSurface }) => (
                  <CommandItem
                    key={`search-lemma-${lemma.lemma}`}
                    value={`wordbank-${lemma.lemma} ${lemma.english_translation ?? ""} ${matchSurface ?? ""}`}
                    onSelect={() => {
                      onOpenWordbankLemma(lemma.lemma)
                      setIsSearchOpen(false)
                      setSearchQuery("")
                    }}
                    className="flex-col items-start gap-0.5"
                  >
                    <span className="font-medium">{lemma.lemma}</span>
                    <span className="text-muted-foreground text-xs">
                      {lemma.english_translation?.trim() || "No translation available."}
                    </span>
                    {matchSurface ? (
                      <span className="text-muted-foreground text-[11px]">
                        Variation match: {matchSurface}
                      </span>
                    ) : null}
                  </CommandItem>
                ))}
                {newWordOptions.map((option) => (
                  <CommandItem
                    key={`${option.action_type}-${option.surface}-${option.lemma}-${option.direction}-${option.pos_tag ?? ""}-${option.morphology ?? ""}`}
                    value={`new-word-${option.surface} ${option.lemma} ${option.translation_label ?? option.surface} ${option.direction_label ?? option.direction} ${normalizedQuery}`}
                    onSelect={() => {
                      void (async () => {
                        const addedLemma = await onAddWordFromSearch(
                          option.surface,
                          option.lemma,
                          {
                            rawToken: normalizedQuery,
                            predictedStatus: activeResolvedCandidate?.classification ?? "new",
                            suggestionsShown: newWordOptions.map((item) => item.translation_label ?? item.surface),
                          },
                          {
                            posTag: option.pos_tag,
                            morphology: option.morphology,
                          },
                        )
                        if (addedLemma) {
                          setIsSearchOpen(false)
                          setSearchQuery("")
                        }
                      })()
                    }}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="flex min-w-0 flex-col items-start gap-0.5">
                      {(() => {
                        const normalizedTranslation = (option.translation_label ?? option.surface).trim().toLocaleLowerCase("da-DK")
                        const normalizedLemma = option.lemma.trim().toLocaleLowerCase("da-DK")
                        const showInlineLemma = option.direction === "en_to_da" && normalizedTranslation !== normalizedLemma
                        return (
                          <>
                      <span className="flex items-baseline gap-2">
                        <span className="font-medium">{option.translation_label ?? option.surface}</span>
                        {showInlineLemma ? (
                          <span className="text-muted-foreground text-xs">({option.lemma})</span>
                        ) : null}
                        <span className="text-muted-foreground text-xs">{option.direction_label ?? option.direction}</span>
                      </span>
                      {option.show_lemma && !showInlineLemma ? (
                        <span className="text-muted-foreground text-xs">lemma: {option.lemma}</span>
                      ) : null}
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {option.pos_tag ? (
                          <Badge
                            variant="secondary"
                            className={`border-border/60 text-xs border ${posBadgeClass(option.pos_tag)}`.trim()}
                            data-testid="search-metadata-badge"
                          >
                            {option.pos_tag}
                          </Badge>
                        ) : null}
                        {option.pos_tag === "NOUN" && determinerWordTypeFromMorphology(option.morphology) ? (
                          <Badge
                            variant="secondary"
                            className="border-border/60 text-xs border"
                            data-testid="search-metadata-badge"
                          >
                            {determinerWordTypeFromMorphology(option.morphology)}
                          </Badge>
                        ) : null}
                        {secondaryTagsForPos(option.pos_tag, option.morphology).map((tag) => (
                          <Badge
                            key={`${option.action_type}-${option.surface}-${option.lemma}-${tag}`}
                            variant="secondary"
                            className="border-border/60 text-xs border"
                            data-testid="search-metadata-badge"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                          </>
                        )
                      })()}
                    </div>
                    <Plus data-testid="search-add-icon" className="text-muted-foreground size-4 shrink-0" />
                  </CommandItem>
                ))}
                {addVariationResult ? (
                  <CommandItem
                    value={`add-variation-${addVariationResult.surface} ${addVariationResult.lemma}`}
                    onSelect={() => {
                      void (async () => {
                        const addedLemma = await onAddWordFromSearch(
                          addVariationResult.surface,
                          addVariationResult.lemma,
                          {
                            rawToken: normalizedQuery,
                            predictedStatus: activeResolvedCandidate?.classification ?? "variation",
                            suggestionsShown: [addVariationResult.translation_label ?? addVariationResult.surface],
                          },
                          {
                            posTag: addVariationResult.pos_tag,
                            morphology: addVariationResult.morphology,
                          },
                        )
                        if (addedLemma) {
                          setIsSearchOpen(false)
                          setSearchQuery("")
                        }
                      })()
                    }}
                    className="flex-col items-start gap-0.5"
                  >
                    <span className="font-medium">
                      Add variation "{addVariationResult.surface}"
                    </span>
                    <span className="text-muted-foreground text-xs">
                      for lemma: {addVariationResult.lemma}
                    </span>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {addVariationResult.pos_tag ? (
                        <Badge
                          variant="secondary"
                          className={`border-border/60 text-xs border ${posBadgeClass(addVariationResult.pos_tag)}`.trim()}
                          data-testid="search-metadata-badge"
                        >
                          {addVariationResult.pos_tag}
                        </Badge>
                      ) : null}
                      {addVariationResult.pos_tag === "NOUN" &&
                      determinerWordTypeFromMorphology(addVariationResult.morphology) ? (
                        <Badge
                          variant="secondary"
                          className="border-border/60 text-xs border"
                          data-testid="search-metadata-badge"
                        >
                          {determinerWordTypeFromMorphology(addVariationResult.morphology)}
                        </Badge>
                        ) : null}
                      {secondaryTagsForPos(addVariationResult.pos_tag, addVariationResult.morphology).map((tag) => (
                        <Badge
                          key={`search-variation-${addVariationResult.surface}-${tag}`}
                          variant="secondary"
                          className="border-border/60 text-xs border"
                          data-testid="search-metadata-badge"
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </CommandItem>
                ) : null}
              </CommandGroup>
            ) : null}
            {(hasWordbankSectionResults || hasWordbankActions) && hasNoteResults ? <CommandSeparator /> : null}
            {hasNoteResults ? (
              <CommandGroup heading="Notes">
                {matchingNotes.map((note) => (
                  <CommandItem
                    key={`search-note-${note.id}`}
                    value={`note-${note.id} ${note.name} ${note.text}`}
                    onSelect={() => {
                      onOpenSavedNote(note.id)
                      setIsSearchOpen(false)
                      setSearchQuery("")
                    }}
                    className="flex-col items-start gap-0.5"
                  >
                    <span className="font-medium">{note.name}</span>
                    <span className="text-muted-foreground line-clamp-2 text-xs">
                      {previewText(note.text, 80)}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}
            {(hasWordbankSectionResults || hasWordbankActions || hasNoteResults) && hasPageResults ? <CommandSeparator /> : null}
            {hasPageResults ? (
              <CommandGroup heading="Pages">
                {matchingPageItems.map((item) => {
                  const Icon = item.icon
                  return (
                    <CommandItem
                      key={item.key}
                      value={item.key}
                      onSelect={() => {
                        item.onSelect()
                        setIsSearchOpen(false)
                      }}
                    >
                      <Icon />
                      <span>{item.label}</span>
                      <CommandShortcut>{item.shortcut}</CommandShortcut>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            ) : null}
          </CommandList>
        </CommandDialog>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "playground"}
                  onClick={onSelectPlayground}
                >
                  <NotebookPen />
                  <span>Playground</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+P</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "notes"}
                  onClick={onSelectNotes}
                >
                  <BookOpen />
                  <span>Notes</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+N</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "wordbank"}
                  onClick={onSelectWordbank}
                >
                  <BookOpen />
                  <span>Wordbank</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+W</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "sentencebank"}
                  onClick={onSelectSentencebank}
                >
                  <BookOpen />
                  <span>Sentencebank</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+S</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "developer"}
                  onClick={onSelectDeveloper}
                >
                  <Settings />
                  <span>Developer</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+D</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <ThemeToggleButton />
      </SidebarFooter>
    </Sidebar>
  )
}

function App() {
  const [status, setStatus] = useState<ConnectionStatus>("loading")
  const [healthPayload, setHealthPayload] = useState<HealthPayload | null>(null)
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [noteText, setNoteText] = useState("")
  const [savedNotes, setSavedNotes] = useState<SavedNote[]>([])
  const [activeNoteId, setActiveNoteId] = useState<string | null>(null)
  const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false)
  const [saveDialogMode, setSaveDialogMode] = useState<SaveDialogMode>("initial")
  const [noteNameDraft, setNoteNameDraft] = useState("")
  const [duplicateNameConflictNoteId, setDuplicateNameConflictNoteId] = useState<string | null>(null)
  const [autosaveStatus, setAutosaveStatus] = useState<"off" | "saving" | "saved">("off")
  const [tokens, setTokens] = useState<AnalyzedToken[]>([])
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisRefreshTick, setAnalysisRefreshTick] = useState(0)
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)
  const [sentencebankRefreshTick, setSentencebankRefreshTick] = useState(0)

  const [lemmas, setLemmas] = useState<WordbankLemma[]>([])
  const [sentences, setSentences] = useState<SentencebankSentence[]>([])
  const [wordbankError, setWordbankError] = useState<string | null>(null)
  const [sentencebankError, setSentencebankError] = useState<string | null>(null)
  const [isWordbankLoading, setIsWordbankLoading] = useState(false)
  const [isSentencebankLoading, setIsSentencebankLoading] = useState(false)
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [lemmaDetails, setLemmaDetails] = useState<LemmaDetailsResponse | null>(null)
  const [lemmaDetailsError, setLemmaDetailsError] = useState<string | null>(null)
  const [isLemmaDetailsLoading, setIsLemmaDetailsLoading] = useState(false)
  const [showLemmaDetailsLoadingSkeleton, setShowLemmaDetailsLoadingSkeleton] = useState(false)
  const [isResettingDatabase, setIsResettingDatabase] = useState(false)
  const [selectedNlpModel, setSelectedNlpModel] = useState<NlpModelOption>(
    NLP_MODEL_OPTIONS[0],
  )
  const [developerTranslationAzureApiKey, setDeveloperTranslationAzureApiKey] = useState("")
  const [developerTranslationAzureRegion, setDeveloperTranslationAzureRegion] = useState("")
  const [developerTranslationAzureEndpoint, setDeveloperTranslationAzureEndpoint] = useState("")
  const [developerTtsAzureApiKey, setDeveloperTtsAzureApiKey] = useState("")
  const [developerTtsAzureRegion, setDeveloperTtsAzureRegion] = useState("")
  const [developerTtsAzureEndpoint, setDeveloperTtsAzureEndpoint] = useState("")
  const [developerVerificationGeminiApiKey, setDeveloperVerificationGeminiApiKey] = useState("")
  const [isSavingDeveloperApiKeys, setIsSavingDeveloperApiKeys] = useState(false)
  const [highlightPopover, setHighlightPopover] = useState<HighlightPopoverState>({
    open: false,
    left: 0,
    lineTop: 0,
    lineBottom: 0,
    side: "bottom",
    tokenIndex: null,
  })
  const [popoverEnrichment, setPopoverEnrichment] = useState<ResolveQueryResponse | null>(null)
  const popoverEnrichmentCacheRef = useRef<Map<string, { payload: ResolveQueryResponse; cachedAt: number }>>(new Map())
  const [phrasePopover, setPhrasePopover] = useState<PhrasePopoverState>({
    open: false,
    left: 0,
    lineTop: 0,
    lineBottom: 0,
    side: "bottom",
    selectedText: "",
  })
  const [discoveredTokenMetadata, setDiscoveredTokenMetadata] = useState<Record<string, DiscoveredTokenMemory>>({})
  const [generatedTranslationMap, setGeneratedTranslationMap] = useState<Record<string, string | null>>({})
  const [isGeneratingTranslation, setIsGeneratingTranslation] = useState(false)
  const [generateTranslationError, setGenerateTranslationError] = useState<string | null>(null)
  const [isGeneratingPhraseTranslation, setIsGeneratingPhraseTranslation] = useState(false)
  const [generatePhraseTranslationError, setGeneratePhraseTranslationError] = useState<string | null>(null)
  const [isRegeneratingLemmaPronunciation, setIsRegeneratingLemmaPronunciation] = useState(false)
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [pronunciationLoadingByForm, setPronunciationLoadingByForm] = useState<Record<string, boolean>>({})
  const [verificationErrorsByLemma, setVerificationErrorsByLemma] = useState<Record<string, VerificationErrorDetail>>({})

  const latestRequestIdRef = useRef(0)
  const activeControllerRef = useRef<AbortController | null>(null)
  const phraseTranslationRequestKeyRef = useRef<string | null>(null)
  const phraseTranslationDelayTimeoutRef = useRef<number | null>(null)
  const lemmaDetailsLoadingDelayTimeoutRef = useRef<number | null>(null)
  const noteAutosaveTimeoutRef = useRef<number | null>(null)
  const pronunciationUrlByFormRef = useRef<Map<string, string>>(new Map())
  const activePronunciationAudioRef = useRef<HTMLAudioElement | null>(null)
  const analysisInput = useMemo(() => finalizedAnalysisText(noteText), [noteText])
  const noteHighlights = useMemo(
    () => mapAnalyzedTokensToHighlights(noteText, tokens),
    [noteText, tokens],
  )
  const groupedWordbankLemmas = useMemo(() => {
    const collator = new Intl.Collator("da", { sensitivity: "base" })
    const sortedLemmas = [...lemmas].sort((left, right) => collator.compare(left.lemma, right.lemma))
    const groups = new Map<string, WordbankLemma[]>()

    for (const lemma of sortedLemmas) {
      const normalizedLemma = lemma.lemma.trim()
      if (!normalizedLemma) {
        continue
      }
      const groupLetter = normalizedLemma[0].toLocaleUpperCase("da-DK")
      if (!groups.has(groupLetter)) {
        groups.set(groupLetter, [])
      }
      groups.get(groupLetter)?.push(lemma)
    }

    return Array.from(groups.entries())
      .sort(([left], [right]) => collator.compare(left, right))
      .map(([letter, items]) => ({ letter, items }))
  }, [lemmas])
  const popoverToken = useMemo(() => {
    if (highlightPopover.tokenIndex === null) {
      return null
    }
    return tokens[highlightPopover.tokenIndex] ?? null
  }, [highlightPopover.tokenIndex, tokens])
  const popoverDisplayToken = useMemo(() => {
    if (!popoverToken) {
      return null
    }
    const key = normalizeWordKey(popoverToken.normalized_token || popoverToken.surface_token)
    const remembered = discoveredTokenMetadata[key]
    if (!remembered) {
      return popoverToken
    }

    if (!isLowConfidencePosTag(popoverToken.pos_tag)) {
      const rememberedForPos = remembered.byPos[popoverToken.pos_tag]
      if (!rememberedForPos) {
        return popoverToken
      }

      return {
        ...popoverToken,
        morphology: popoverToken.morphology ?? rememberedForPos.morphology,
        lemma_candidate: popoverToken.lemma_candidate ?? rememberedForPos.lemma,
        lemma: rememberedForPos.lemma,
      }
    }

    return {
      ...popoverToken,
      pos_tag: remembered.latest.pos_tag,
      morphology: popoverToken.morphology ?? remembered.latest.morphology,
      lemma_candidate: popoverToken.lemma_candidate ?? remembered.latest.lemma,
      lemma: remembered.latest.lemma,
    }
  }, [discoveredTokenMetadata, popoverToken])
  const popoverTranslation = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    for (const key of translationKeysForToken(popoverDisplayToken)) {
      if (Object.hasOwn(generatedTranslationMap, key)) {
        return generatedTranslationMap[key] ?? null
      }
    }
    return null
  }, [generatedTranslationMap, popoverDisplayToken])
  const popoverLemma = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    return popoverDisplayToken.matched_lemma ?? popoverDisplayToken.lemma_candidate ?? null
  }, [popoverDisplayToken])
  const selectedLemmaVerificationError = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    return verificationErrorsByLemma[lemmaKey] ?? null
  }, [lemmaDetails?.lemma, selectedLemma, verificationErrorsByLemma])
  const popoverPrimaryAction = (() => {
    if (!popoverDisplayToken) {
      return null
    }
    const tokenActions = popoverEnrichment?.word_actions ?? popoverDisplayToken.word_actions ?? []
    return tokenActions[0] ?? null
  })()

  const popoverIsNoun = popoverDisplayToken?.pos_tag === "NOUN"
  const popoverIsVerbLike = popoverDisplayToken?.pos_tag === "VERB" || popoverDisplayToken?.pos_tag === "AUX"
  const unreadNotifications = useMemo(
    () => notifications.filter((notification) => !notification.read),
    [notifications],
  )
  const hasUnreadNotifications = unreadNotifications.length > 0
  const activeSavedNote = useMemo(
    () => savedNotes.find((note) => note.id === activeNoteId) ?? null,
    [activeNoteId, savedNotes],
  )
  const activeSavedNoteId = activeSavedNote?.id ?? null
  const activeSavedNoteName = activeSavedNote?.name ?? null
  const popoverLemmaText = popoverLemma?.trim() ?? null
  const popoverSurfaceText = popoverDisplayToken?.surface_token?.trim() ?? null
  const showPopoverLemma = Boolean(
    popoverLemmaText &&
    popoverSurfaceText &&
    popoverLemmaText.toLocaleLowerCase("da-DK") !== popoverSurfaceText.toLocaleLowerCase("da-DK"),
  )
  const popoverMetadataBadges = useMemo(() => {
    if (!popoverDisplayToken) {
      return []
    }
    return [
      popoverDisplayToken.pos_tag
        ? {
          key: `popover-meta-pos-${popoverDisplayToken.pos_tag}`,
          label: popoverDisplayToken.pos_tag,
          className: posBadgeClass(popoverDisplayToken.pos_tag),
        }
        : null,
      ...(popoverDisplayToken.pos_tag === "NOUN"
        ? [determinerWordTypeFromMorphology(popoverDisplayToken.morphology)]
        : []
      ).filter((value): value is string => Boolean(value)).map((value) => ({
        key: `popover-meta-wordtype-${value}`,
        label: value,
        className: "",
      })),
      ...secondaryTagsForPos(popoverDisplayToken.pos_tag, popoverDisplayToken.morphology).map((value) => ({
        key: `popover-meta-tag-${value}`,
        label: value,
        className: "",
      })),
    ].filter((value): value is { key: string; label: string; className: string } => Boolean(value))
  }, [popoverDisplayToken])
  const showTranslationSkeleton = isGeneratingTranslation || (
    (popoverIsNoun || popoverIsVerbLike) &&
    (!popoverTranslation || Boolean(generateTranslationError))
  )
  const phraseTranslation = useMemo(() => {
    const phraseKey = normalizePhraseKey(phrasePopover.selectedText)
    if (!phraseKey || !Object.hasOwn(generatedTranslationMap, phraseKey)) {
      return null
    }
    return generatedTranslationMap[phraseKey] ?? null
  }, [generatedTranslationMap, phrasePopover.selectedText])
  const isSelectedPhraseSaved = useMemo(() => {
    const phraseKey = normalizePhraseKey(phrasePopover.selectedText)
    if (!phraseKey) {
      return false
    }
    return sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === phraseKey)
  }, [phrasePopover.selectedText, sentences])
  const apiStatusItems = useMemo(() => {
    const apis = healthPayload?.apis ?? {}
    const priorityOrder = ["backend", "azure_translator", "azure_speech"]
    const orderedNames = [
      ...priorityOrder.filter((name) => Object.hasOwn(apis, name)),
      ...Object.keys(apis).filter((name) => !priorityOrder.includes(name)).sort(),
    ]

    if (orderedNames.length === 0) {
      return [
        {
          name: "backend",
          label: "Backend API",
          status: status === "connected" ? "ok" : status === "degraded" ? "degraded" : "unknown",
          message: null as string | null,
        },
      ]
    }

    return orderedNames.map((name) => {
      const entry = apis[name] ?? {}
      return {
        name,
        label: humanizeApiName(name),
        status: normalizeApiRuntimeStatus(entry.status),
        message: entry.message ?? null,
      }
    })
  }, [healthPayload, status])

  useEffect(() => {
    setSavedNotes(loadSavedNotes())
  }, [])

  useEffect(() => {
    persistSavedNotes(savedNotes)
  }, [savedNotes])

  useEffect(() => {
    if (!activeSavedNoteId || !activeSavedNoteName) {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
      setAutosaveStatus("off")
      return
    }

    setAutosaveStatus("saving")
    if (noteAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(noteAutosaveTimeoutRef.current)
    }
    noteAutosaveTimeoutRef.current = window.setTimeout(() => {
      noteAutosaveTimeoutRef.current = null
      const savedAt = new Date().toISOString()
      const nextNote: SavedNote = {
        id: activeSavedNoteId,
        name: activeSavedNoteName,
        text: noteText,
        tokens: [...tokens],
        discoveredTokenMetadata: { ...discoveredTokenMetadata },
        generatedTranslationMap: { ...generatedTranslationMap },
        savedAt,
      }

      setSavedNotes((current) => {
        const existingIndex = current.findIndex((note) => note.id === activeSavedNoteId)
        if (existingIndex === -1) {
          return [nextNote, ...current]
        }
        const next = [...current]
        next[existingIndex] = nextNote
        return next
      })
      setAutosaveStatus("saved")
    }, NOTE_AUTOSAVE_DEBOUNCE_MS)

    return () => {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
    }
  }, [
    activeSavedNoteId,
    activeSavedNoteName,
    discoveredTokenMetadata,
    generatedTranslationMap,
    noteText,
    tokens,
  ])

  useEffect(() => {
    if (tokens.length === 0) {
      return
    }

    setDiscoveredTokenMetadata((current) => {
      let changed = false
      const next = { ...current }
      for (const token of tokens) {
        if (isLowConfidencePosTag(token.pos_tag)) {
          continue
        }
        const key = normalizeWordKey(token.normalized_token || token.surface_token)
        const lemma = token.matched_lemma ?? token.lemma_candidate ?? null
        const candidate: DiscoveredTokenMetadata = {
          pos_tag: token.pos_tag,
          morphology: token.morphology,
          lemma,
        }
        const existing = next[key]
        const existingForPos = existing?.byPos[candidate.pos_tag]

        if (
          !existing ||
          !existingForPos ||
          existingForPos.morphology !== candidate.morphology ||
          existingForPos.lemma !== candidate.lemma ||
          existing.latest.pos_tag !== candidate.pos_tag ||
          existing.latest.morphology !== candidate.morphology ||
          existing.latest.lemma !== candidate.lemma
        ) {
          next[key] = {
            latest: candidate,
            byPos: {
              ...(existing?.byPos ?? {}),
              [candidate.pos_tag]: candidate,
            },
          }
          changed = true
        }
      }
      return changed ? next : current
    })
  }, [tokens])

  useEffect(() => {
    let cancelled = false

    async function checkHealth() {
      try {
        const response = await fetch(`${BACKEND_URL}/api/health`)
        if (!cancelled && response.ok) {
          const payload = (await response.json()) as HealthPayload
          setHealthPayload(payload)
          if (payload.status === "ok") {
            setStatus("connected")
            return
          }
          if (payload.status === "degraded") {
            setStatus("degraded")
            return
          }
          setStatus("offline")
          setHealthPayload(null)
          return
        }
      } catch {
        // ignore and set offline below
      }

      if (!cancelled) {
        setStatus("offline")
        setHealthPayload(null)
      }
    }

    checkHealth()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!analysisInput) {
      activeControllerRef.current?.abort()
      setAnalysisError(null)
      setTokens([])
      return
    }

    const timeoutId = window.setTimeout(async () => {
      const requestId = latestRequestIdRef.current + 1
      latestRequestIdRef.current = requestId

      activeControllerRef.current?.abort()
      const controller = new AbortController()
      activeControllerRef.current = controller

      setAnalysisError(null)
      try {
        const response = await fetch(`${BACKEND_URL}/api/analyze`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text: analysisInput }),
          signal: controller.signal,
        })

        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Analyze request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const payload = (await response.json()) as { tokens: AnalyzedToken[] }
        if (requestId === latestRequestIdRef.current) {
          setTokens(payload.tokens ?? [])
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return
        }
        if (requestId === latestRequestIdRef.current) {
          const message = error instanceof Error ? error.message : "Could not analyze notes."
          setAnalysisError(message)
          setTokens([])
        }
        void error
      }
    }, ANALYZE_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [analysisInput, analysisRefreshTick])

  useEffect(() => {
    return () => {
      activeControllerRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    const pronunciationUrlByForm = pronunciationUrlByFormRef.current
    return () => {
      for (const url of pronunciationUrlByForm.values()) {
        URL.revokeObjectURL(url)
      }
      pronunciationUrlByForm.clear()
      const activeAudio = activePronunciationAudioRef.current
      if (activeAudio) {
        activeAudio.pause()
        activePronunciationAudioRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setIsWordbankLoading(true)
    setWordbankError(null)

    void (async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/wordbank/lemmas`)
        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Wordbank request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const payload = (await response.json()) as LemmaListResponse
        if (!cancelled) {
          setLemmas(payload.items ?? [])
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load wordbank."
          setWordbankError(message)
          setLemmas([])
        }
        void error
      } finally {
        if (!cancelled) {
          setIsWordbankLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [wordbankRefreshTick])

  useEffect(() => {
    let cancelled = false
    setIsSentencebankLoading(true)
    setSentencebankError(null)

    void (async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/sentencebank/sentences`)
        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Sentencebank request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const payload = (await response.json()) as SentenceListResponse
        if (!cancelled) {
          setSentences(payload.items ?? [])
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load sentencebank."
          setSentencebankError(message)
          setSentences([])
        }
        void error
      } finally {
        if (!cancelled) {
          setIsSentencebankLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [sentencebankRefreshTick])

  useEffect(() => {
    if (activeSection !== "wordbank" || !selectedLemma) {
      if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
        window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
        lemmaDetailsLoadingDelayTimeoutRef.current = null
      }
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      setIsLemmaDetailsLoading(false)
      setShowLemmaDetailsLoadingSkeleton(false)
      return
    }

    let cancelled = false
    setIsLemmaDetailsLoading(true)
    setLemmaDetailsError(null)
    setShowLemmaDetailsLoadingSkeleton(false)
    lemmaDetailsLoadingDelayTimeoutRef.current = window.setTimeout(() => {
      if (!cancelled) {
        setShowLemmaDetailsLoadingSkeleton(true)
      }
    }, 180)

    void (async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/api/wordbank/lemmas/${encodeURIComponent(selectedLemma)}`,
        )
        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Word details request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const payload = (await response.json()) as LemmaDetailsResponse
        if (!cancelled) {
          setLemmaDetails(payload)
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load lemma details."
          setLemmaDetailsError(message)
          setLemmaDetails(null)
        }
        void error
      } finally {
        if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
          window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
          lemmaDetailsLoadingDelayTimeoutRef.current = null
        }
        if (!cancelled) {
          setIsLemmaDetailsLoading(false)
          setShowLemmaDetailsLoadingSkeleton(false)
        }
      }
    })()

    return () => {
      cancelled = true
      if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
        window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
        lemmaDetailsLoadingDelayTimeoutRef.current = null
      }
    }
  }, [activeSection, selectedLemma, wordbankRefreshTick])

  useEffect(() => {
    setPronunciationLoadingByForm({})
    setIsRegeneratingLemmaPronunciation(false)
  }, [selectedLemma])

  useEffect(() => {
    if (!highlightPopover.open) {
      return
    }
    if (highlightPopover.tokenIndex === null || !tokens[highlightPopover.tokenIndex]) {
      setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    }
  }, [highlightPopover.open, highlightPopover.tokenIndex, tokens])

  useEffect(() => {
    if (!highlightPopover.open || !popoverDisplayToken) {
      setPopoverEnrichment(null)
      return
    }

    const tokenValue = normalizeSearchWord(popoverDisplayToken.normalized_token || popoverDisplayToken.surface_token)
    if (!tokenValue) {
      setPopoverEnrichment(null)
      return
    }

    const cacheKey = normalizeWordKey(tokenValue)
    const cached = popoverEnrichmentCacheRef.current.get(cacheKey)
    if (cached && Date.now() - cached.cachedAt < POPOVER_ENRICH_CACHE_TTL_MS) {
      setPopoverEnrichment(cached.payload)
      if (cached.payload.da_to_en_translation) {
        setGeneratedTranslationMap((current) => ({
          ...current,
          [cacheKey]: cached.payload.da_to_en_translation,
        }))
      }
      return
    }

    let cancelled = false
    const controller = new AbortController()

    void (async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/analyze/enrich-token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: tokenValue,
            include_translations: true,
            include_language_detection: true,
          }),
          signal: controller.signal,
        })
        if (!response.ok) {
          return
        }

        const payload = (await response.json()) as ResolveQueryResponse
        if (cancelled) {
          return
        }
        popoverEnrichmentCacheRef.current.set(cacheKey, {
          payload,
          cachedAt: Date.now(),
        })
        setPopoverEnrichment(payload)
        if (payload.da_to_en_translation) {
          setGeneratedTranslationMap((current) => ({
            ...current,
            [cacheKey]: payload.da_to_en_translation,
          }))
        }
      } catch {
        // ignore enrichment failures for popover fallback behavior
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [highlightPopover.open, popoverDisplayToken])


  const badgeVariant =
    status === "connected"
      ? "secondary"
      : status === "degraded"
        ? "outline"
        : status === "offline"
          ? "destructive"
          : "outline"
  const autosaveStatusLabel =
    autosaveStatus === "saving"
      ? "Autosaving..."
      : autosaveStatus === "saved"
        ? "Autosaved"
        : "Autosave off"

  function clearPronunciationCache(form: string | null | undefined) {
    const normalizedForm = normalizeSearchWord(form ?? "")
    if (!normalizedForm) {
      return
    }
    const objectUrl = pronunciationUrlByFormRef.current.get(normalizedForm)
    if (!objectUrl) {
      return
    }
    const activeAudio = activePronunciationAudioRef.current
    if (activeAudio?.src === objectUrl) {
      activeAudio.pause()
      activePronunciationAudioRef.current = null
    }
    URL.revokeObjectURL(objectUrl)
    pronunciationUrlByFormRef.current.delete(normalizedForm)
  }

  async function playPronunciation(form: string) {
    const normalizedForm = normalizeSearchWord(form)
    if (!normalizedForm) {
      return
    }

    setPronunciationLoadingByForm((current) => ({ ...current, [normalizedForm]: true }))
    try {
      let didRepair = false
      while (true) {
        let objectUrl = pronunciationUrlByFormRef.current.get(normalizedForm)
        if (!objectUrl) {
          const response = await fetch(
            `${BACKEND_URL}/api/wordbank/pronunciation?form=${encodeURIComponent(normalizedForm)}`,
          )
          if (!response.ok) {
            if (response.status === 404) {
              toast.error(`No pronunciation is available yet for '${normalizedForm}'.`)
              return
            }
            const message = await extractErrorMessage(
              response,
              `Pronunciation request failed with status ${response.status}`,
            )
            throw new Error(message)
          }

          const contentType = typeof response.headers?.get === "function"
            ? response.headers.get("content-type")
            : null
          if (!isPlayableAudioContentType(contentType)) {
            throw new Error(`Unsupported pronunciation format: ${contentType}`)
          }
          const audioBlob = await response.blob()
          objectUrl = URL.createObjectURL(audioBlob)
          pronunciationUrlByFormRef.current.set(normalizedForm, objectUrl)
        }

        if (activePronunciationAudioRef.current) {
          activePronunciationAudioRef.current.pause()
        }
        const audio = new Audio(objectUrl)
        activePronunciationAudioRef.current = audio
        try {
          await audio.play()
          break
        } catch (error) {
          if (!didRepair && isUnsupportedAudioError(error)) {
            didRepair = true
            clearPronunciationCache(normalizedForm)
            const selectedLemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? normalizedForm)
            const storedSurface = normalizedForm === selectedLemmaKey ? selectedLemmaKey : normalizedForm
            await generatePronunciationInBackground(selectedLemmaKey, storedSurface, { force: true, notify: false })
            continue
          }
          throw error
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not play pronunciation."
      toast.error(message)
      void error
    } finally {
      setPronunciationLoadingByForm((current) => {
        const next = { ...current }
        delete next[normalizedForm]
        return next
      })
    }
  }

  async function addWordToWordbank(
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ): Promise<AddWordResponse> {
    const normalizedSurfaceToken = normalizeSearchWord(surfaceToken)
    const normalizedLemmaCandidate = lemmaCandidate ? normalizeSearchWord(lemmaCandidate) : null
    const normalizedPosTag = metadata?.posTag?.trim() || null
    const normalizedMorphology = metadata?.morphology?.trim() || null
    const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        {
          surface_token: normalizedSurfaceToken,
          lemma_candidate: normalizedLemmaCandidate,
          ...(normalizedPosTag ? { pos_tag: normalizedPosTag } : {}),
          ...(normalizedMorphology ? { morphology: normalizedMorphology } : {}),
        },
      ),
    })

    if (!response.ok) {
      const message = await extractErrorMessage(
        response,
        `Add word request failed with status ${response.status}`,
      )
      throw new Error(message)
    }

    return (await response.json()) as AddWordResponse
  }

  async function addTokenToWordbank(token: AnalyzedToken, action?: WordActionSuggestion) {
    const requestSurface = action?.surface ?? (token.normalized_token || token.surface_token)
    const requestLemma = action?.lemma ?? token.lemma_candidate
    const loadingKey = addLoadingKey(token)

    setAddingTokens((current) => ({ ...current, [loadingKey]: true }))

    try {
      const payload = await addWordToWordbank(requestSurface, requestLemma, {
        posTag: action?.pos_tag,
        morphology: action?.morphology,
      })
      toast.success(payload.message)
      void verifyWordInBackground(payload.stored_lemma, payload.stored_surface_form)
      void generatePronunciationInBackground(payload.stored_lemma, payload.stored_surface_form)
      void postTokenFeedback({
        raw_token: token.surface_token,
        predicted_status: token.classification,
        suggestions_shown: (token.suggestions ?? []).map((item) => item.value),
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
        source: "playground",
      })
      setAnalysisRefreshTick((current) => current + 1)
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add word to wordbank. Try again."
      toast.error(message)
      void error
    } finally {
      setAddingTokens((current) => {
        const next = { ...current }
        delete next[loadingKey]
        return next
      })
    }
  }

  async function addWordFromSearch(
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ): Promise<string | null> {
    try {
      const payload = await addWordToWordbank(surfaceToken, lemmaCandidate, metadata)
      toast.success(payload.message)
      void verifyWordInBackground(payload.stored_lemma, payload.stored_surface_form)
      void generatePronunciationInBackground(payload.stored_lemma, payload.stored_surface_form)
      void postTokenFeedback({
        raw_token: feedbackContext?.rawToken ?? surfaceToken,
        predicted_status: feedbackContext?.predictedStatus ?? "new",
        suggestions_shown: feedbackContext?.suggestionsShown ?? [],
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
        source: "search",
      })
      setAnalysisRefreshTick((current) => current + 1)
      setWordbankRefreshTick((current) => current + 1)
      setActiveSection("wordbank")
      setSelectedLemma(payload.stored_lemma)
      return payload.stored_lemma
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add word to wordbank. Try again."
      toast.error(message)
      return null
    }
  }

  async function generateTranslationForToken(token: AnalyzedToken) {
    const sourceWord = normalizeSearchWord(token.normalized_token || token.surface_token)
    const requestSurface = normalizeSearchWord(token.normalized_token || token.surface_token)
    const requestLemma = normalizeSearchWord(token.matched_lemma ?? token.lemma_candidate ?? "") || null
    const tokenKeys = translationKeysForToken(token)
    const hasResolvedTranslation = tokenKeys.some((key) => {
      if (!Object.hasOwn(generatedTranslationMap, key)) {
        return false
      }
      return generatedTranslationMap[key] !== null
    })
    if (hasResolvedTranslation) {
      return
    }

    setIsGeneratingTranslation(true)
    setGenerateTranslationError(null)
    try {
      let payload: GenerateTranslationResponse | null = null
      let translation: string | null = null
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const response = await fetch(`${BACKEND_URL}/api/wordbank/translation`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            surface_token: requestSurface,
            lemma_candidate: requestLemma,
          }),
        })
        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Translation request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const nextPayload = (await response.json()) as GenerateTranslationResponse
        const nextTranslation = nextPayload.english_translation?.trim() || null
        payload = nextPayload
        translation = nextTranslation
        if (nextTranslation) {
          break
        }
      }

      if (!payload) {
        return
      }

      const responseKey = normalizeWordKey(payload.source_word || sourceWord)

      setGeneratedTranslationMap((current) => {
        const next = { ...current }
        for (const key of [...tokenKeys, responseKey]) {
          if (!key) {
            continue
          }
          if (next[key] === undefined || (next[key] === null && translation !== null)) {
            next[key] = translation
          }
        }
        return next
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate translation."
      setGenerateTranslationError(message)
      void error
    } finally {
      setIsGeneratingTranslation(false)
    }
  }

  async function generateTranslationForPhrase(selectedText: string) {
    const phraseKey = normalizePhraseKey(selectedText)
    if (!phraseKey || Object.hasOwn(generatedTranslationMap, phraseKey)) {
      setIsGeneratingPhraseTranslation(false)
      return
    }

    if (phraseTranslationDelayTimeoutRef.current !== null) {
      window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
      phraseTranslationDelayTimeoutRef.current = null
    }

    phraseTranslationRequestKeyRef.current = phraseKey
    setIsGeneratingPhraseTranslation(true)
    setGeneratePhraseTranslationError(null)
    phraseTranslationDelayTimeoutRef.current = window.setTimeout(() => {
      phraseTranslationDelayTimeoutRef.current = null
      void (async () => {
        try {
          const response = await fetch(`${BACKEND_URL}/api/wordbank/phrase-translation`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              source_text: selectedText,
            }),
          })
          if (!response.ok) {
            const message = await extractErrorMessage(
              response,
              `Phrase translation request failed with status ${response.status}`,
            )
            throw new Error(message)
          }

          const payload = (await response.json()) as GeneratePhraseTranslationResponse
          const responseKey = normalizePhraseKey(payload.source_text || selectedText)
          const translation = payload.english_translation?.trim() || null

          setGeneratedTranslationMap((current) => {
            const next = { ...current }
            if (responseKey) {
              next[responseKey] = translation
            }
            if (phraseKey) {
              next[phraseKey] = translation
            }
            return next
          })
        } catch (error) {
          if (phraseTranslationRequestKeyRef.current === phraseKey) {
            const message = error instanceof Error ? error.message : "Could not generate phrase translation."
            setGeneratePhraseTranslationError(message)
          }
          void error
        } finally {
          if (phraseTranslationRequestKeyRef.current === phraseKey) {
            setIsGeneratingPhraseTranslation(false)
          }
        }
      })()
    }, PHRASE_TRANSLATION_DELAY_MS)
  }

  async function addSentenceToSentencebank(selectedText: string) {
    const normalizedSelection = selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      return
    }
    const selectionKey = normalizePhraseKey(normalizedSelection)
    if (sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === selectionKey)) {
      return
    }

    setIsSavingSentence(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/sentencebank/sentences`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_text: normalizedSelection,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Save sentence request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as AddSentenceResponse
      toast.success(payload.message)
      setSentencebankRefreshTick((current) => current + 1)
      setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence. Try again."
      toast.error(message)
      void error
    } finally {
      setIsSavingSentence(false)
    }
  }

  function openHighlightPopover(tokenIndex: number, left: number, lineTop: number, lineBottom: number) {
    const token = tokens[tokenIndex]
    if (!token || token.classification === "typo_likely" || token.pos_tag === "PROPN" || token.pos_tag === "NUM") {
      return
    }

    const side = preferredPopoverSide(lineTop, lineBottom)
    setHighlightPopover({ open: true, tokenIndex, left, lineTop, lineBottom, side })
    setPhrasePopover((current) => ({ ...current, open: false }))
    void generateTranslationForToken(token)
  }

  function handleEditorSelection(payload: {
    selectedText: string
    left: number
    lineTop: number
    lineBottom: number
  } | null) {
    if (!payload) {
      if (phraseTranslationDelayTimeoutRef.current !== null) {
        window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
        phraseTranslationDelayTimeoutRef.current = null
      }
      setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
      setGeneratePhraseTranslationError(null)
      setIsGeneratingPhraseTranslation(false)
      return
    }

    const normalizedSelection = payload.selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      if (phraseTranslationDelayTimeoutRef.current !== null) {
        window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
        phraseTranslationDelayTimeoutRef.current = null
      }
      setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
      setGeneratePhraseTranslationError(null)
      setIsGeneratingPhraseTranslation(false)
      return
    }

    const side = preferredPopoverSide(payload.lineTop, payload.lineBottom)
    setPhrasePopover({
      open: true,
      selectedText: normalizedSelection,
      left: payload.left,
      lineTop: payload.lineTop,
      lineBottom: payload.lineBottom,
      side,
    })
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    void generateTranslationForPhrase(normalizedSelection)
  }

  useEffect(() => {
    return () => {
      if (phraseTranslationDelayTimeoutRef.current !== null) {
        window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
      }
    }
  }, [])



  async function postTokenFeedback(payload: TokenFeedbackPayload) {
    try {
      await fetch(`${BACKEND_URL}/api/tokens/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
    } catch {
      // Feedback logging is best-effort in v1.
    }
  }

  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the complete database and cannot be undone. Continue?",
    )
    if (!shouldReset) {
      return
    }

    setIsResettingDatabase(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/database`, {
        method: "DELETE",
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Reset database request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ResetDatabaseResponse
      toast.success(payload.message)

      setNoteText("")
      setTokens([])
      setAnalysisError(null)
      setSelectedLemma(null)
      setLemmas([])
      setSentences([])
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      setVerificationErrorsByLemma({})
      setWordbankRefreshTick((current) => current + 1)
      setSentencebankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not reset database."
      toast.error(message)
      void error
    } finally {
      setIsResettingDatabase(false)
    }
  }

  function openSaveDialog() {
    if (activeSavedNote) {
      setSaveDialogMode("create_new")
      setNoteNameDraft(`Note ${savedNotes.length + 1}`)
    } else {
      setSaveDialogMode("initial")
      setNoteNameDraft(`Note ${savedNotes.length + 1}`)
    }
    setDuplicateNameConflictNoteId(null)
    setIsSaveDialogOpen(true)
  }

  function pushNotification(message: string) {
    const createdAt = new Date().toISOString()
    const nextNotification: AppNotification = {
      id: createNotificationId(),
      message,
      createdAt,
      read: false,
    }

    setNotifications((current) => [nextNotification, ...current])
  }

  function hasSuggestedVerificationChanges(detail: VerificationErrorDetail | null): boolean {
    if (!detail?.suggestedChangesPayload) {
      return false
    }
    return Object.values(detail.suggestedChangesPayload).some((value) => typeof value === "string" && value.trim().length > 0)
  }

  async function applySelectedLemmaVerificationChanges() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    const detail = verificationErrorsByLemma[lemma] ?? null
    if (!detail || !hasSuggestedVerificationChanges(detail) || !detail.suggestedChangesPayload) {
      return
    }

    setIsApplyingVerificationChanges(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes/apply-verification-changes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: lemma,
          stored_surface_form: detail.storedSurfaceForm ?? lemma,
          suggested_changes: detail.suggestedChangesPayload,
          provider: detail.provider,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Apply verification changes failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ApplyVerificationChangesResponse
      if (payload.status === "applied") {
        const count = payload.applied_fields.length
        toast.success(
          count > 0
            ? `Applied ${count} Gemini change${count === 1 ? "" : "s"} for '${lemma}'.`
            : `Applied Gemini changes for '${lemma}'.`,
        )
        setVerificationErrorsByLemma((current) => {
          if (!Object.hasOwn(current, lemma)) {
            return current
          }
          const next = { ...current }
          delete next[lemma]
          return next
        })
        setWordbankRefreshTick((current) => current + 1)
      } else {
        toast.error("No Gemini changes were applied.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not apply Gemini changes."
      toast.error(message)
    } finally {
      setIsApplyingVerificationChanges(false)
    }
  }

  function notifyWordVerification(
    storedLemma: string,
    storedSurfaceForm: string | null,
    verification: VerifyWordResponse["verification"],
  ) {
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
      return
    }

    const isOk = verification.status === "verified"
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (isOk) {
      setVerificationErrorsByLemma((current) => {
        if (!Object.hasOwn(current, lemmaKey)) {
          return current
        }
        const next = { ...current }
        delete next[lemmaKey]
        return next
      })
      pushNotification("OK")
      return
    }

    const detail = buildVerificationErrorDetail({
      provider: verification.provider,
      status: verification.status === "flagged" ? "flagged" : "error",
      message: verification.message,
      composedWordCount: verification.composed_word_count,
      storedSurfaceForm,
      problem: verification.problem,
      changeToImplement: verification.change_to_implement,
      suggestedChanges: verification.suggested_changes,
    })
    setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
    const displayLemma = lemmaKey || storedLemma || "word"
    pushNotification(`ERROR ${displayLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
  }

  async function verifyWordInBackground(storedLemma: string, storedSurfaceForm: string | null) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Verify word request failed with status ${response.status}`,
        )
        throw new Error(message)
      }
      const payload = (await response.json()) as VerifyWordResponse
      notifyWordVerification(payload.stored_lemma, payload.stored_surface_form, payload.verification)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const lemmaKey = normalizeSearchWord(storedLemma)
      const detail = buildVerificationErrorDetail({
        provider: "gemini",
        status: "error",
        message,
        storedSurfaceForm,
      })
      setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
      pushNotification(`ERROR ${lemmaKey || storedLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
    }
  }

  async function generatePronunciationInBackground(
    storedLemma: string,
    storedSurfaceForm: string | null,
    options?: { force?: boolean; notify?: boolean },
  ) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes/pronunciation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
          force: Boolean(options?.force),
        }),
      })
      if (!response.ok) {
        if (options?.notify) {
          const message = await extractErrorMessage(
            response,
            `Pronunciation request failed with status ${response.status}`,
          )
          toast.error(message)
        }
        return
      }
      const payload = (await response.json()) as GeneratePronunciationResponse
      clearPronunciationCache(payload.pronunciation_form)
      if (payload.status === "generated") {
        setWordbankRefreshTick((current) => current + 1)
        if (options?.notify) {
          toast.success(`Regenerated pronunciation for '${payload.pronunciation_form ?? storedLemma}'.`)
        }
      } else if (options?.notify) {
        toast.error(`Could not regenerate pronunciation for '${payload.pronunciation_form ?? storedLemma}'.`)
      }
    } catch {
      if (options?.notify) {
        toast.error("Could not regenerate pronunciation.")
      }
      // Keep add flow instant; pronunciation generation is best effort.
    }
  }

  async function regenerateSelectedLemmaPronunciation() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    setIsRegeneratingLemmaPronunciation(true)
    try {
      await generatePronunciationInBackground(lemma, lemma, { force: true, notify: true })
    } finally {
      setIsRegeneratingLemmaPronunciation(false)
    }
  }

  function markAllNotificationsAsRead() {
    setNotifications((current) => current.map((notification) => ({ ...notification, read: true })))
  }

  function findDuplicateNameNoteId(name: string, excludedNoteId: string | null): string | null {
    const normalized = name.trim().toLocaleLowerCase()
    if (!normalized) {
      return null
    }
    const duplicate = savedNotes.find(
      (note) => note.id !== excludedNoteId && note.name.trim().toLocaleLowerCase() === normalized,
    )
    return duplicate?.id ?? null
  }

  function saveCurrentNote(
    name: string,
    options?: {
      forceNew?: boolean
      forcedNoteId?: string
      silent?: boolean
    },
  ) {
    if (!name) {
      toast.error("Note name is required.")
      return
    }

    const forceNew = options?.forceNew ?? false
    const excludedNoteId = forceNew ? null : (options?.forcedNoteId ?? activeSavedNote?.id ?? null)
    const duplicateNameNoteId = findDuplicateNameNoteId(name, excludedNoteId)
    if (duplicateNameNoteId) {
      setDuplicateNameConflictNoteId(duplicateNameNoteId)
      return
    }

    const savedAt = new Date().toISOString()
    const noteId = options?.forcedNoteId ?? (forceNew ? undefined : activeSavedNote?.id) ?? createSavedNoteId()
    const nextNote: SavedNote = {
      id: noteId,
      name,
      text: noteText,
      tokens: [...tokens],
      discoveredTokenMetadata: { ...discoveredTokenMetadata },
      generatedTranslationMap: { ...generatedTranslationMap },
      savedAt,
    }

    setSavedNotes((current) => {
      const existingIndex = current.findIndex((note) => note.id === noteId)
      if (existingIndex === -1) {
        return [nextNote, ...current]
      }
      const next = [...current]
      next[existingIndex] = nextNote
      return next
    })
    setActiveNoteId(noteId)
    setDuplicateNameConflictNoteId(null)
    setAutosaveStatus("saved")
    setIsSaveDialogOpen(false)
    if (!options?.silent) {
      toast.success("Note saved.")
      pushNotification(`Saved note: ${name}`)
    }
  }

  function saveActiveNoteSilently() {
    if (!activeSavedNote) {
      return
    }
    const savedAt = new Date().toISOString()
    const nextNote: SavedNote = {
      id: activeSavedNote.id,
      name: activeSavedNote.name,
      text: noteText,
      tokens: [...tokens],
      discoveredTokenMetadata: { ...discoveredTokenMetadata },
      generatedTranslationMap: { ...generatedTranslationMap },
      savedAt,
    }

    setSavedNotes((current) => {
      const existingIndex = current.findIndex((note) => note.id === nextNote.id)
      if (existingIndex === -1) {
        return [nextNote, ...current]
      }
      const next = [...current]
      next[existingIndex] = nextNote
      return next
    })
    setAutosaveStatus("saved")
  }

  function createNewNamedNote(name: string) {
    if (!name) {
      toast.error("Note name is required.")
      return
    }

    const duplicateNameNoteId = findDuplicateNameNoteId(name, null)
    if (duplicateNameNoteId) {
      setDuplicateNameConflictNoteId(duplicateNameNoteId)
      return
    }

    if (noteAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(noteAutosaveTimeoutRef.current)
      noteAutosaveTimeoutRef.current = null
    }
    saveActiveNoteSilently()

    const savedAt = new Date().toISOString()
    const noteId = createSavedNoteId()
    const nextNote: SavedNote = {
      id: noteId,
      name,
      text: "",
      tokens: [],
      discoveredTokenMetadata: {},
      generatedTranslationMap: {},
      savedAt,
    }

    setSavedNotes((current) => [nextNote, ...current])
    setActiveNoteId(noteId)
    setNoteText("")
    setTokens([])
    setDiscoveredTokenMetadata({})
    setGeneratedTranslationMap({})
    setAnalysisError(null)
    setGeneratePhraseTranslationError(null)
    setGenerateTranslationError(null)
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
    setDuplicateNameConflictNoteId(null)
    setAutosaveStatus("saved")
    setIsSaveDialogOpen(false)
    toast.success("New note created.")
    pushNotification(`Created new note: ${name}`)
  }

  function openSavedNoteInPlayground(note: SavedNote) {
    setNoteText(note.text)
    setTokens(note.tokens)
    setDiscoveredTokenMetadata(note.discoveredTokenMetadata)
    setGeneratedTranslationMap(note.generatedTranslationMap)
    setAnalysisError(null)
    setGeneratePhraseTranslationError(null)
    setGenerateTranslationError(null)
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
    setActiveNoteId(note.id)
    setAutosaveStatus("saved")
    setActiveSection("playground")
  }

  function openSavedNoteById(noteId: string) {
    const note = savedNotes.find((candidate) => candidate.id === noteId)
    if (!note) {
      return
    }
    openSavedNoteInPlayground(note)
  }

  function renderWordbankContent() {
    if (!selectedLemma) {
      return (
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          {wordbankError && (
            <p className="text-destructive text-sm" role="alert">
              {wordbankError}
            </p>
          )}
          {isWordbankLoading && lemmas.length === 0 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Skeleton className="h-3 w-4" />
                <div className="flex flex-wrap gap-2">
                  <Skeleton className="h-8 w-16 rounded-md" />
                  <Skeleton className="h-8 w-20 rounded-md" />
                  <Skeleton className="h-8 w-14 rounded-md" />
                  <Skeleton className="h-8 w-24 rounded-md" />
                </div>
              </div>
              <div className="space-y-2">
                <Skeleton className="h-3 w-4" />
                <div className="flex flex-wrap gap-2">
                  <Skeleton className="h-8 w-[4.5rem] rounded-md" />
                  <Skeleton className="h-8 w-12 rounded-md" />
                  <Skeleton className="h-8 w-[5.5rem] rounded-md" />
                </div>
              </div>
              <div className="space-y-2">
                <Skeleton className="h-3 w-4" />
                <div className="flex flex-wrap gap-2">
                  <Skeleton className="h-8 w-[3.75rem] rounded-md" />
                  <Skeleton className="h-8 w-[4.75rem] rounded-md" />
                  <Skeleton className="h-8 w-[2.75rem] rounded-md" />
                  <Skeleton className="h-8 w-[4.25rem] rounded-md" />
                </div>
              </div>
            </div>
          ) : lemmas.length === 0 ? (
            <p className="text-muted-foreground text-sm">No saved lemmas yet.</p>
          ) : (
            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4">
                {groupedWordbankLemmas.map((group) => (
                  <section key={group.letter} className="space-y-2">
                    <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{group.letter}</h3>
                    <div className="flex flex-wrap gap-2">
                      {group.items.map((lemma) => (
                        <Button
                          key={lemma.lemma}
                          type="button"
                          variant="outline"
                          size="sm"
                          className="w-auto"
                          onClick={() => setSelectedLemma(lemma.lemma)}
                        >
                          {lemma.display_lemma?.trim() || lemma.lemma}
                        </Button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      )
    }

    const normalizedSelectedLemma = (lemmaDetails?.lemma ?? selectedLemma).trim().toLocaleLowerCase("da-DK")
    const lemmaPronunciationForm = (() => {
      if (!lemmaDetails) {
        return null
      }
      const exactMatch = lemmaDetails.surface_forms.find(
        (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma && form.has_pronunciation,
      )
      if (exactMatch) {
        return exactMatch.form
      }
      const firstAvailable = lemmaDetails.surface_forms.find((form) => form.has_pronunciation)
      return firstAvailable?.form ?? null
    })()
    const variationForms = lemmaDetails?.surface_forms.filter(
      (form) => form.form.trim().toLocaleLowerCase("da-DK") !== normalizedSelectedLemma,
    ) ?? []
    const lemmaMetadataBadges = lemmaDetails
      ? [
        lemmaDetails.pos_tag
          ? {
            key: `lemma-meta-pos-${lemmaDetails.pos_tag}`,
            label: lemmaDetails.pos_tag,
            className: posBadgeClass(lemmaDetails.pos_tag),
          }
          : null,
        ...(lemmaDetails.pos_tag === "NOUN"
          ? [determinerWordTypeFromMorphology(lemmaDetails.morphology)]
          : []
        ).filter((value): value is string => Boolean(value)).map((value) => ({
          key: `lemma-meta-wordtype-${value}`,
          label: value,
          className: "",
        })),
        ...secondaryTagsForPos(lemmaDetails.pos_tag, lemmaDetails.morphology).map((value) => ({
          key: `lemma-meta-tag-${value}`,
          label: value,
          className: "",
        })),
      ].filter((value): value is { key: string; label: string; className: string } => Boolean(value))
      : []

    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4">
        {lemmaDetailsError && (
          <p className="text-destructive text-sm" role="alert">
            {lemmaDetailsError}
          </p>
        )}
        {isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton ? (
          <div className="space-y-3">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Skeleton className="h-10 w-40" />
                <Skeleton className="h-5 w-14 rounded-full" />
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Card>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <Skeleton className="h-6 w-24" />
                  </div>
                  <Skeleton className="h-4 w-28" />
                  <div className="flex flex-wrap gap-1.5">
                    <Skeleton className="h-5 w-12 rounded-full" />
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-4 w-14" />
                  </div>
                  <Skeleton className="h-4 w-24" />
                  <div className="flex flex-wrap gap-1.5">
                    <Skeleton className="h-5 w-16 rounded-full" />
                    <Skeleton className="h-5 w-10 rounded-full" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : !lemmaDetails ? (
          isLemmaDetailsLoading ? null : (
          <p className="text-muted-foreground text-sm">No details found for this lemma.</p>
          )
        ) : (
          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-3 pr-1">
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                    <h2 className="mr-3 text-4xl font-bold leading-tight">{lemmaDetails.lemma}</h2>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon-sm"
                            aria-label={`Listen to ${lemmaDetails.lemma}`}
                            disabled={
                              !lemmaPronunciationForm
                              || Boolean(pronunciationLoadingByForm[normalizeSearchWord(lemmaPronunciationForm)])
                            }
                            onClick={(event) => {
                              event.currentTarget.blur()
                              if (!lemmaPronunciationForm) {
                                return
                              }
                              void playPronunciation(lemmaPronunciationForm)
                            }}
                          >
                            <Volume2 />
                          </Button>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="right" sideOffset={6}>
                        <p>Listen</p>
                      </TooltipContent>
                    </Tooltip>
                    {lemmaMetadataBadges.map((badge) => (
                      <Badge key={badge.key} variant="secondary" className={`text-xs ${badge.className}`.trim()}>
                        {badge.label}
                      </Badge>
                    ))}
                  </div>
                  <ButtonGroup className="shrink-0">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isRegeneratingLemmaPronunciation}
                      onClick={() => {
                        void regenerateSelectedLemmaPronunciation()
                      }}
                    >
                      <RefreshCw className={isRegeneratingLemmaPronunciation ? "animate-spin" : ""} />
                      Regenerate Audio
                    </Button>
                    <Popover>
                      <PopoverTrigger asChild>
                        <span>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            aria-label="Show verification error info"
                            disabled={!selectedLemmaVerificationError}
                          >
                            <Info className="size-4" />
                          </Button>
                        </span>
                      </PopoverTrigger>
                      <PopoverContent align="end" className="w-96 space-y-3">
                        {!selectedLemmaVerificationError ? (
                          <p className="text-muted-foreground text-sm">No verification errors for this word.</p>
                        ) : (
                          <>
                            <div>
                              <p className="text-sm font-semibold">Verification Error</p>
                              <p className="text-muted-foreground text-xs">
                                Provider: {selectedLemmaVerificationError.provider}
                              </p>
                            </div>
                            <div className="space-y-1">
                              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                                Problem
                              </p>
                              <p className="text-sm">{selectedLemmaVerificationError.problem}</p>
                            </div>
                            <div className="space-y-1">
                              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                                Change to implement
                              </p>
                              <p className="text-sm">{selectedLemmaVerificationError.changeToImplement}</p>
                            </div>
                            {selectedLemmaVerificationError.suggestedChanges
                              && Object.values(selectedLemmaVerificationError.suggestedChanges).some(Boolean) ? (
                                <div className="space-y-1">
                                  <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                                    Specific fields to change
                                  </p>
                                  <ul className="space-y-1 text-sm">
                                    {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag ? (
                                      <li>Lemma POS: {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag}</li>
                                    ) : null}
                                    {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology ? (
                                      <li>Lemma morphology: {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology}</li>
                                    ) : null}
                                    {selectedLemmaVerificationError.suggestedChanges.surfacePosTag ? (
                                      <li>Surface POS: {selectedLemmaVerificationError.suggestedChanges.surfacePosTag}</li>
                                    ) : null}
                                    {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology ? (
                                      <li>Surface morphology: {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology}</li>
                                    ) : null}
                                    {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation ? (
                                      <li>Lemma translation: {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation}</li>
                                    ) : null}
                                    {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation ? (
                                      <li>Surface translation: {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation}</li>
                                    ) : null}
                                  </ul>
                                </div>
                              ) : null}
                            <Button
                              type="button"
                              size="sm"
                              className="w-full"
                              disabled={!hasSuggestedVerificationChanges(selectedLemmaVerificationError) || isApplyingVerificationChanges}
                              onClick={() => {
                                void applySelectedLemmaVerificationChanges()
                              }}
                            >
                              {isApplyingVerificationChanges ? "Applying..." : "Apply Gemini Changes"}
                            </Button>
                          </>
                        )}
                      </PopoverContent>
                    </Popover>
                  </ButtonGroup>
                </div>
                <p className="text-muted-foreground mt-1 text-base">
                  {lemmaDetails.english_translation ?? "No translation available."}
                </p>
              </div>

              {variationForms.length === 0 ? (
                <p className="text-muted-foreground text-sm">No saved variations for this lemma.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {variationForms.map((form) => {
                    return (
                      <Card key={form.form}>
                        <CardContent className="space-y-3">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-lg font-bold leading-tight">{form.form}</p>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="icon-sm"
                                    aria-label={`Listen to ${form.form}`}
                                    disabled={
                                      !form.has_pronunciation
                                      || Boolean(pronunciationLoadingByForm[normalizeSearchWord(form.form)])
                                    }
                                    onClick={(event) => {
                                      event.currentTarget.blur()
                                      void playPronunciation(form.form)
                                    }}
                                  >
                                    <Volume2 />
                                  </Button>
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="right" sideOffset={6}>
                                <p>Listen</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <p className="text-muted-foreground text-sm">
                            {form.english_translation ?? "No translation available."}
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {form.pos_tag && (
                              <Badge variant="secondary" className={posBadgeClass(form.pos_tag)}>
                                {form.pos_tag}
                              </Badge>
                            )}
                            {secondaryTagsForPos(form.pos_tag, form.morphology).map((tag) => (
                              <Badge key={`${form.form}-${tag}`} variant="secondary">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    )
  }

  function renderPlaygroundContent() {
    return (
      <div className="space-y-4">
        <Dialog
          open={isSaveDialogOpen}
          onOpenChange={(open) => {
            setIsSaveDialogOpen(open)
            if (!open) {
              setDuplicateNameConflictNoteId(null)
            }
          }}
        >
          <DialogContent>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                if (saveDialogMode === "create_new") {
                  createNewNamedNote(noteNameDraft.trim())
                  return
                }
                saveCurrentNote(noteNameDraft.trim())
              }}
            >
              <DialogHeader>
                <DialogTitle>{saveDialogMode === "create_new" ? "Create new note" : "Save note"}</DialogTitle>
                {saveDialogMode === "create_new" ? (
                  <DialogDescription>
                    The current note will be saved. Creating a new note clears the editor.
                  </DialogDescription>
                ) : (
                  <DialogDescription>Name this note to store text and analysis.</DialogDescription>
                )}
              </DialogHeader>
              {saveDialogMode === "create_new" ? (
                <div className="space-y-2">
                  <Label htmlFor="save-note-name-new">New note name</Label>
                  <Input
                    id="save-note-name-new"
                    value={noteNameDraft}
                    onChange={(event) => {
                      setNoteNameDraft(event.target.value)
                      setDuplicateNameConflictNoteId(null)
                    }}
                    placeholder="My Danish note copy"
                    autoComplete="off"
                    autoFocus
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="save-note-name">Note name</Label>
                  <Input
                    id="save-note-name"
                    value={noteNameDraft}
                    onChange={(event) => {
                      setNoteNameDraft(event.target.value)
                      setDuplicateNameConflictNoteId(null)
                    }}
                    placeholder="My Danish note"
                    autoComplete="off"
                    autoFocus
                  />
                </div>
              )}
              {duplicateNameConflictNoteId ? (
                <p className="text-muted-foreground text-sm">
                  {saveDialogMode === "create_new"
                    ? "A note with this title already exists. Use it or change the name."
                    : "A note with this title already exists. Overwrite it or change the name."}
                </p>
              ) : null}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsSaveDialogOpen(false)}>
                  Cancel
                </Button>
                {duplicateNameConflictNoteId ? (
                  <Button
                    type="button"
                    onClick={() => {
                      if (saveDialogMode === "create_new") {
                        if (noteAutosaveTimeoutRef.current !== null) {
                          window.clearTimeout(noteAutosaveTimeoutRef.current)
                          noteAutosaveTimeoutRef.current = null
                        }
                        saveActiveNoteSilently()
                        setActiveNoteId(duplicateNameConflictNoteId)
                        setDuplicateNameConflictNoteId(null)
                        setIsSaveDialogOpen(false)
                        toast.success("Opened existing note for autosave.")
                        return
                      }
                      saveCurrentNote(noteNameDraft.trim(), { forcedNoteId: duplicateNameConflictNoteId })
                    }}
                  >
                    {saveDialogMode === "create_new" ? "Use existing note" : "Overwrite existing"}
                  </Button>
                ) : null}
                {saveDialogMode === "create_new" ? (
                  <Button type="submit">Create new note</Button>
                ) : (
                  <Button type="submit">Save</Button>
                )}
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
        <div className="relative">
          <Popover
            open={phrasePopover.open && Boolean(phrasePopover.selectedText)}
            onOpenChange={(open) => {
              setPhrasePopover((current) => ({
                ...current,
                open,
                selectedText: open ? current.selectedText : "",
              }))
              if (!open) {
                setGeneratePhraseTranslationError(null)
              }
            }}
          >
            <PopoverAnchor asChild>
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                className="pointer-events-none fixed size-px opacity-0"
                style={{
                  left: phrasePopover.left,
                  top: phrasePopover.side === "bottom" ? phrasePopover.lineBottom : phrasePopover.lineTop,
                }}
              />
            </PopoverAnchor>
            <PopoverContent
              side={phrasePopover.side}
              align="start"
              sideOffset={8}
              onOpenAutoFocus={(event) => {
                event.preventDefault()
              }}
              className={`${PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS} space-y-2`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className={`space-y-1 ${PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS} min-w-0`}>
                  <p className="text-sm font-semibold leading-snug break-words">{phrasePopover.selectedText}</p>
                  {isGeneratingPhraseTranslation && !phraseTranslation ? (
                    <Skeleton data-testid="phrase-translation-skeleton" className="h-4 w-28" />
                  ) : generatePhraseTranslationError ? (
                    <p className="text-destructive text-xs">{generatePhraseTranslationError}</p>
                  ) : phraseTranslation ? (
                    <p className="text-muted-foreground text-sm break-words">{phraseTranslation}</p>
                  ) : (
                    <p className="text-muted-foreground text-xs">No translation available.</p>
                  )}
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex">
                      <Button
                        type="button"
                        variant="default"
                        size="icon-sm"
                        aria-label="Add to sentencebank"
                        disabled={isSavingSentence || isSelectedPhraseSaved}
                        onClick={() => {
                          void addSentenceToSentencebank(phrasePopover.selectedText)
                        }}
                      >
                        <Plus />
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={6}>
                    <p>{isSelectedPhraseSaved ? "Already in sentencebank" : isSavingSentence ? "Saving..." : "Add to sentencebank"}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </PopoverContent>
          </Popover>
          <Popover
            open={highlightPopover.open && Boolean(popoverDisplayToken)}
            onOpenChange={(open) => {
              setHighlightPopover((current) => ({
                ...current,
                open,
                tokenIndex: open ? current.tokenIndex : null,
              }))
            }}
          >
            <PopoverAnchor asChild>
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                className="pointer-events-none fixed size-px opacity-0"
                style={{
                  left: highlightPopover.left,
                  top: highlightPopover.side === "bottom" ? highlightPopover.lineBottom : highlightPopover.lineTop,
                }}
              />
            </PopoverAnchor>
            <PopoverContent
              side={highlightPopover.side}
              align="start"
              sideOffset={8}
              onOpenAutoFocus={(event) => {
                event.preventDefault()
              }}
              className="w-fit max-w-[calc(100vw-1rem)] space-y-3"
            >
              {popoverDisplayToken && (
                <>
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5">
                      {popoverDisplayToken.surface_token ? (
                        <div className="flex flex-wrap items-baseline gap-1.5">
                          <p className="text-2xl font-bold leading-tight">{popoverDisplayToken.surface_token}</p>
                          {showPopoverLemma ? (
                            <p className="text-muted-foreground text-sm font-normal leading-tight">({popoverLemmaText})</p>
                          ) : null}
                        </div>
                      ) : (
                        <Skeleton data-testid="word-skeleton" className="h-7 w-28" />
                      )}
                      <div className="flex shrink-0 flex-nowrap items-center gap-1">
                        {popoverMetadataBadges.map((badge) => (
                          <Badge key={badge.key} variant="secondary" className={`text-xs ${badge.className}`.trim()}>
                            {badge.label}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    {showTranslationSkeleton ? (
                      <Skeleton
                        data-testid={popoverIsNoun ? "noun-translation-skeleton" : popoverIsVerbLike ? "verb-translation-skeleton" : "translation-skeleton"}
                        className="h-4 w-24"
                      />
                    ) : generateTranslationError ? (
                      <p className="text-destructive text-xs">{generateTranslationError}</p>
                    ) : popoverTranslation ? (
                      <p className="text-muted-foreground text-sm">{popoverTranslation}</p>
                    ) : (
                      <p className="text-muted-foreground text-xs">No translation available.</p>
                    )}
                    <div className="mt-2.5 flex items-center justify-end gap-2">
                      {popoverPrimaryAction?.action_type === "open_wordbank" ? (
                        <Tooltip><TooltipTrigger asChild><span className="inline-flex">
                          <Button type="button" variant="default" size="icon-sm" aria-label="Open in wordbank" disabled={!popoverPrimaryAction.lemma} onClick={() => {
                            setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
                            setActiveSection("wordbank")
                            setSelectedLemma(popoverPrimaryAction.lemma)
                          }}><Eye /></Button>
                        </span></TooltipTrigger><TooltipContent side="right" sideOffset={6}><p>Open in wordbank</p></TooltipContent></Tooltip>
                      ) : popoverPrimaryAction ? (
                        <Tooltip><TooltipTrigger asChild><span className="inline-flex">
                          <Button type="button" variant="default" size="icon-sm" aria-label={popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"} disabled={Boolean(addingTokens[addLoadingKey(popoverDisplayToken)])} onClick={() => {
                            void addTokenToWordbank(popoverDisplayToken, popoverPrimaryAction)
                            setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
                          }}><Plus /></Button>
                        </span></TooltipTrigger><TooltipContent side="right" sideOffset={6}><p>{popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"}</p></TooltipContent></Tooltip>
                      ) : null}
                    </div>
                  </div>
                </>
              )}
            </PopoverContent>
          </Popover>
          <NotesEditor
            id="lesson-notes"
            placeholder="Type lesson notes here..."
            value={noteText}
            highlights={noteHighlights}
            onChange={(nextText) => {
              setNoteText(nextText)
              if (highlightPopover.open) {
                setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
              }
              if (phrasePopover.open) {
                setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
              }
              if (phraseTranslationDelayTimeoutRef.current !== null) {
                window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
                phraseTranslationDelayTimeoutRef.current = null
              }
              setGeneratePhraseTranslationError(null)
              setIsGeneratingPhraseTranslation(false)
            }}
            onHighlightClick={({ tokenIndex, left, lineTop, lineBottom }) => {
              openHighlightPopover(tokenIndex, left, lineTop, lineBottom)
            }}
            onTextSelectionSettled={handleEditorSelection}
          />
          <p className="text-muted-foreground absolute right-3 bottom-2 text-xs" aria-label="note-character-count">
            {noteText.length}
          </p>
        </div>
        {analysisError && (
          <p className="text-destructive mt-2 text-sm" role="alert">
            {analysisError}
          </p>
        )}
      </div>
    )
  }

  function renderNotesContent() {
    if (savedNotes.length === 0) {
      return <p className="text-muted-foreground text-sm">No saved notes yet. Save one from Playground.</p>
    }

    return (
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {savedNotes.map((note) => {
          return (
            <Card key={note.id} className="p-0">
              <button
                type="button"
                className="hover:bg-accent/60 focus-visible:ring-ring w-full rounded-lg p-4 text-left outline-none transition-colors hover:cursor-pointer focus-visible:ring-2"
                onClick={() => {
                  openSavedNoteInPlayground(note)
                }}
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <CardTitle className="text-base leading-tight">{note.name}</CardTitle>
                  <p className="text-muted-foreground text-xs">{formatSavedNoteTimestamp(note.savedAt)}</p>
                </div>
                <p className="text-muted-foreground text-sm leading-relaxed">{previewText(note.text)}</p>
              </button>
            </Card>
          )
        })}
      </div>
    )
  }

  function renderSentencebankContent() {
    if (sentencebankError) {
      return (
        <p className="text-destructive text-sm" role="alert">
          {sentencebankError}
        </p>
      )
    }

    if (isSentencebankLoading && sentences.length === 0) {
      return (
        <div className="space-y-3">
          <Card>
            <CardContent className="space-y-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-4 w-32" />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="space-y-2">
              <Skeleton className="h-5 w-56" />
              <Skeleton className="h-4 w-36" />
            </CardContent>
          </Card>
        </div>
      )
    }

    if (sentences.length === 0) {
      return <p className="text-muted-foreground text-sm">No saved sentences yet. Select a sentence in Playground to add one.</p>
    }

    return (
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-3 pr-1">
          {sentences.map((sentence) => (
            <Card key={sentence.id}>
              <CardContent className="space-y-2">
                <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
                <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
                  {sentence.english_translation?.trim() || "No translation available."}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    )
  }


  async function saveDeveloperApiKeys() {
    setIsSavingDeveloperApiKeys(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/developer/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          translation_azure_api_key: developerTranslationAzureApiKey,
          translation_azure_region: developerTranslationAzureRegion,
          translation_azure_endpoint: developerTranslationAzureEndpoint,
          tts_azure_api_key: developerTtsAzureApiKey,
          tts_azure_region: developerTtsAzureRegion,
          tts_azure_endpoint: developerTtsAzureEndpoint,
          word_verification_gemini_api_key: developerVerificationGeminiApiKey,
        }),
      })

      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Save API keys request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as DeveloperApiKeysUpdateResponse
      toast.success(payload.message || "Runtime API keys updated.")

      const healthResponse = await fetch(`${BACKEND_URL}/api/health`)
      if (healthResponse.ok) {
        const payload = (await healthResponse.json()) as HealthPayload
        setHealthPayload(payload)
        setStatus(payload.status === "ok" ? "connected" : payload.status === "degraded" ? "degraded" : "offline")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save API keys."
      toast.error(message)
    } finally {
      setIsSavingDeveloperApiKeys(false)
    }
  }

  function renderDeveloperContent() {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Developer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Backend status</span>
            <Badge variant={badgeVariant} aria-label="backend-connection-status">
              {status}
            </Badge>
          </div>
          <div className="text-muted-foreground text-sm">
            Backend: <code>{BACKEND_URL}</code>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">API status</p>
            <div className="space-y-2" aria-label="api-status-list">
              {apiStatusItems.map((item) => (
                <div key={item.name} className="rounded-md border p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm">{item.label}</span>
                    <Badge variant="outline" className={apiStatusBadgeClass(item.status)}>
                      {humanizeApiStatus(item.status)}
                    </Badge>
                  </div>
                  {item.message ? (
                    <p className="text-muted-foreground mt-1 text-xs">{item.message}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">NLP model</p>
            <Select value={selectedNlpModel} onValueChange={(value) => setSelectedNlpModel(value as NlpModelOption)}>
              <SelectTrigger aria-label="NLP model picker" className="w-full max-w-sm">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {NLP_MODEL_OPTIONS.map((model) => (
                  <SelectItem key={model} value={model}>
                    {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-muted-foreground text-xs">
              Preferred model for local benchmarking. Backend default remains <code>da_dacy_small_trf-0.2.0</code> unless
              <code> DANOTE_NLP_MODEL</code> is set before startup.
            </p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Runtime API keys</p>
            <p className="text-muted-foreground text-xs">
              Keys entered here apply immediately for this backend process and are not persisted to source code.
            </p>
            <div className="space-y-1">
              <Label htmlFor="developer-translation-azure-key">Azure Translator API key</Label>
              <Input
                id="developer-translation-azure-key"
                type="password"
                value={developerTranslationAzureApiKey}
                onChange={(event) => setDeveloperTranslationAzureApiKey(event.target.value)}
                placeholder="Paste Azure Translator key"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-translation-azure-region">Azure Translator region</Label>
              <Input
                id="developer-translation-azure-region"
                value={developerTranslationAzureRegion}
                onChange={(event) => setDeveloperTranslationAzureRegion(event.target.value)}
                placeholder="e.g. westeurope"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-translation-azure-endpoint">Azure Translator endpoint (optional)</Label>
              <Input
                id="developer-translation-azure-endpoint"
                value={developerTranslationAzureEndpoint}
                onChange={(event) => setDeveloperTranslationAzureEndpoint(event.target.value)}
                placeholder="https://api.cognitive.microsofttranslator.com"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-tts-azure-key">Azure Speech API key</Label>
              <Input
                id="developer-tts-azure-key"
                type="password"
                value={developerTtsAzureApiKey}
                onChange={(event) => setDeveloperTtsAzureApiKey(event.target.value)}
                placeholder="Paste Azure Speech key"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-tts-azure-region">Azure Speech region</Label>
              <Input
                id="developer-tts-azure-region"
                value={developerTtsAzureRegion}
                onChange={(event) => setDeveloperTtsAzureRegion(event.target.value)}
                placeholder="e.g. westeurope"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-tts-azure-endpoint">Azure Speech endpoint (optional)</Label>
              <Input
                id="developer-tts-azure-endpoint"
                value={developerTtsAzureEndpoint}
                onChange={(event) => setDeveloperTtsAzureEndpoint(event.target.value)}
                placeholder="https://<resource>.cognitiveservices.azure.com"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-verification-key">Word verification Gemini key</Label>
              <Input
                id="developer-verification-key"
                type="password"
                value={developerVerificationGeminiApiKey}
                onChange={(event) => setDeveloperVerificationGeminiApiKey(event.target.value)}
                placeholder="Paste Gemini key for verification"
              />
            </div>
            <Button type="button" size="sm" onClick={() => { void saveDeveloperApiKeys() }} disabled={isSavingDeveloperApiKeys}>
              {isSavingDeveloperApiKeys ? "Saving..." : "Apply runtime API keys"}
            </Button>
          </div>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            disabled={isResettingDatabase}
            onClick={() => {
              void resetDatabase()
            }}
          >
            {isResettingDatabase ? "Deleting..." : "Delete complete DB"}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        savedNotes={savedNotes}
        onSelectPlayground={() => {
          setActiveSection("playground")
        }}
        onSelectNotes={() => {
          setActiveSection("notes")
          setSelectedLemma(null)
        }}
        onSelectWordbank={() => {
          setActiveSection("wordbank")
          setSelectedLemma(null)
        }}
        onSelectSentencebank={() => {
          setActiveSection("sentencebank")
          setSelectedLemma(null)
        }}
        onSelectDeveloper={() => {
          setActiveSection("developer")
          setSelectedLemma(null)
        }}
        onOpenWordbankLemma={(lemma) => {
          setActiveSection("wordbank")
          setSelectedLemma(lemma)
        }}
        onOpenSavedNote={openSavedNoteById}
        onAddWordFromSearch={addWordFromSearch}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger />
          <span className="text-sm font-medium">Danote</span>
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col px-1 pt-3 pb-2 md:px-2 md:pt-8 md:pb-4">
          <span className="sr-only" aria-label="backend-connection-status">
            {status}
          </span>
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
            <div className="mb-6 md:mb-8 flex items-center justify-between gap-3">
              <AppBreadcrumb
                activeSection={activeSection}
                selectedLemma={selectedLemma}
                activeNoteName={activeSavedNote?.name ?? null}
                onSelectWordbank={() => {
                  setActiveSection("wordbank")
                  setSelectedLemma(null)
                }}
              />
              {activeSection === "playground" ? (
                <div className="flex items-center gap-2">
                  <p className="text-muted-foreground text-xs" aria-label="note-autosave-status">
                    {autosaveStatusLabel}
                  </p>
                  <ButtonGroup>
                    <ButtonGroup>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="gap-1.5"
                        onClick={openSaveDialog}
                      >
                        <Save className="size-3.5" />
                        {activeSavedNote ? "Create new note" : "Save note"}
                      </Button>
                    </ButtonGroup>
                    <ButtonGroup>
                      <Popover
                        open={isNotificationsOpen}
                        onOpenChange={(open) => {
                          setIsNotificationsOpen(open)
                          if (open && hasUnreadNotifications) {
                            markAllNotificationsAsRead()
                          }
                        }}
                      >
                        <PopoverTrigger asChild>
                          <Button
                            type="button"
                            size="sm"
                            variant={hasUnreadNotifications ? "default" : "outline"}
                            className="gap-1.5"
                            aria-label={
                              hasUnreadNotifications
                                ? `Show notifications (${unreadNotifications.length} unread)`
                                : "No unread notifications"
                            }
                            disabled={!hasUnreadNotifications}
                          >
                            <Bell className="size-3.5" />
                            {hasUnreadNotifications ? (
                              <span className="text-[11px] leading-none">{unreadNotifications.length}</span>
                            ) : null}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent align="end" className="w-80 space-y-2">
                          <p className="text-sm font-medium">Notifications</p>
                          {notifications.length === 0 ? (
                            <p className="text-muted-foreground text-xs">No notifications yet.</p>
                          ) : (
                            <ul className="space-y-2" aria-label="notification-list">
                              {notifications.map((notification) => (
                                <li key={notification.id} className="rounded-md border px-3 py-2">
                                  <div className="flex items-center justify-between gap-2">
                                    <p className="text-sm">{notification.message}</p>
                                    {!notification.read ? <Badge variant="secondary">New</Badge> : null}
                                  </div>
                                  <p className="text-muted-foreground mt-1 text-xs">
                                    {formatSavedNoteTimestamp(notification.createdAt)}
                                  </p>
                                </li>
                              ))}
                            </ul>
                          )}
                        </PopoverContent>
                      </Popover>
                    </ButtonGroup>
                  </ButtonGroup>
                </div>
              ) : null}
            </div>
              {activeSection === "playground"
              ? renderPlaygroundContent()
              : activeSection === "notes"
                ? renderNotesContent()
              : activeSection === "wordbank"
                ? renderWordbankContent()
                : activeSection === "sentencebank"
                  ? renderSentencebankContent()
                : renderDeveloperContent()}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
