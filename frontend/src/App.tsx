import { useEffect, useMemo, useRef, useState } from "react"
import { BookOpen, Moon, NotebookPen, Save, Settings, Sun } from "lucide-react"
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
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
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
type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
type AppSection = "playground" | "notes" | "wordbank" | "developer"
type TokenAction = "add_as_new"

type AnalyzedToken = {
  surface_token: string
  normalized_token: string
  lemma_candidate: string | null
  pos_tag: string | null
  morphology: string | null
  classification: TokenClassification
  status: TokenClassification
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
  surface: string
  normalized: string
  lemma: string | null
}

type AddWordResponse = {
  status: "inserted" | "exists"
  stored_lemma: string
  stored_surface_form: string | null
  source: "manual"
  message: string
}

type WordbankLemma = {
  lemma: string
  english_translation: string | null
  variation_count: number
}

type LemmaListResponse = {
  items: WordbankLemma[]
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

type GeneratePhraseTranslationResponse = {
  status: "generated" | "cached" | "unavailable"
  source_text: string
  english_translation: string | null
}

type TokenFeedbackPayload = {
  raw_token: string
  predicted_status: string
  suggestions_shown: string[]
  user_action: TokenAction
  chosen_value?: string
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

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
const ANALYZE_DEBOUNCE_MS = 450
const PHRASE_TRANSLATION_DELAY_MS = 1000
const NLP_MODEL_OPTIONS = [
  "da_dacy_small_trf-0.2.0",
  "da_dacy_medium_trf-0.2.0",
  "da_dacy_large_trf-0.2.0",
] as const
const POPOVER_VIEWPORT_MARGIN_PX = 12
const POPOVER_ESTIMATED_HEIGHT_PX = 280
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

function nounArticleFromMorphology(morphology: string | null): "en" | "et" | null {
  if (!morphology) {
    return null
  }
  if (/(^|\|)Gender=Com(\||$)/u.test(morphology)) {
    return "en"
  }
  if (/(^|\|)Gender=Neut(\||$)/u.test(morphology)) {
    return "et"
  }
  return null
}

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

function lemmaLabelForPos(lemma: string, posTag: string | null, morphology: string | null): string {
  if (posTag === "NOUN") {
    const article = nounArticleFromMorphology(morphology)
    return article ? `${lemma} (${article})` : lemma
  }
  if (posTag === "VERB" || posTag === "AUX") {
    return `at ${lemma}`
  }
  return lemma
}

function shouldShowLemmaLabel(surface: string, lemmaLabel: string, posTag: string | null): boolean {
  return posTag === "NOUN" || lemmaLabel !== surface
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
  onSelectDeveloper: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenSavedNote: (noteId: string) => void
  onAddWordFromSearch: (surfaceToken: string, lemmaCandidate: string | null) => Promise<string | null>
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
  onSelectDeveloper,
  onOpenWordbankLemma,
  onOpenSavedNote,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [resolvedQueryCandidate, setResolvedQueryCandidate] = useState<{
    query: string
    surface: string
    lemma: string | null
    classification: TokenClassification
    translation: string | null
    matchedLemma: WordbankLemma | null
  } | null>(null)
  const trimmedQuery = searchQuery.trim()
  const normalizedQuery = trimmedQuery.toLocaleLowerCase("da-DK")
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
  const wordbankResults = useMemo(() => {
    const variationMatch = activeResolvedCandidate?.matchedLemma
      ? {
        lemma: activeResolvedCandidate.matchedLemma,
        surface: activeResolvedCandidate.surface,
      }
      : null
    const directMatches = matchingLemmas.map((lemma) => ({
      lemma,
      matchSurface: null as string | null,
    }))

    if (!variationMatch) {
      return directMatches
    }

    const hasLemma = directMatches.some((item) => item.lemma.lemma === variationMatch.lemma.lemma)
    if (hasLemma) {
      return directMatches
    }

    return [{ lemma: variationMatch.lemma, matchSurface: variationMatch.surface }, ...directMatches]
  }, [activeResolvedCandidate, matchingLemmas])
  const hasWordbankResults = wordbankResults.length > 0
  const newWordResult = useMemo(() => {
    if (!activeResolvedCandidate || hasWordbankResults) {
      return null
    }
    if (activeResolvedCandidate.classification === "typo_likely") {
      return null
    }

    const lemma = activeResolvedCandidate.lemma?.trim() || activeResolvedCandidate.surface.trim()
    if (!lemma) {
      return null
    }

    return {
      surface: activeResolvedCandidate.surface,
      lemma,
      translation: activeResolvedCandidate.translation,
    }
  }, [activeResolvedCandidate, hasWordbankResults])
  const addVariationResult = useMemo(() => {
    if (!activeResolvedCandidate?.matchedLemma) {
      return null
    }
    if (activeResolvedCandidate.classification !== "variation") {
      return null
    }
    const surface = activeResolvedCandidate.surface.trim()
    const lemma = activeResolvedCandidate.matchedLemma.lemma.trim()
    if (!surface || !lemma || surface.toLocaleLowerCase("da-DK") === lemma.toLocaleLowerCase("da-DK")) {
      return null
    }
    return {
      surface,
      lemma,
    }
  }, [activeResolvedCandidate])
  const hasWordbankSectionResults = hasWordbankResults || Boolean(newWordResult)
  const hasWordbankActions = Boolean(newWordResult) || Boolean(addVariationResult)
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
        key: "page-developer",
        label: "Developer",
        shortcut: "Alt+D",
        icon: Settings,
        onSelect: onSelectDeveloper,
      },
    ],
    [onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectWordbank],
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
      if (key === "d") {
        event.preventDefault()
        onSelectDeveloper()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectWordbank])

  useEffect(() => {
    if (!normalizedQuery || /\s/u.test(normalizedQuery)) {
      return
    }

    const alreadyDirectMatch = matchingLemmas.some(
      (lemma) => lemma.lemma.trim().toLocaleLowerCase("da-DK") === normalizedQuery,
    )
    if (alreadyDirectMatch) {
      return
    }

    const controller = new AbortController()
    let cancelled = false

    void (async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/analyze`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: trimmedQuery,
          }),
          signal: controller.signal,
        })
        if (!response.ok) {
          setResolvedQueryCandidate((current) => (current?.query === normalizedQuery ? null : current))
          return
        }
        const payload = (await response.json()) as { tokens?: AnalyzedToken[] }
        const token = payload.tokens?.[0]
        if (!token || cancelled) {
          setResolvedQueryCandidate((current) => (current?.query === normalizedQuery ? null : current))
          return
        }
        const matchedLemmaKey = token.matched_lemma?.trim().toLocaleLowerCase("da-DK") ?? null
        const resolvedLemma = matchedLemmaKey
          ? lemmas.find((lemma) => lemma.lemma.trim().toLocaleLowerCase("da-DK") === matchedLemmaKey) ?? null
          : null

        if (resolvedLemma) {
          setResolvedQueryCandidate({
            query: normalizedQuery,
            surface: token.surface_token || trimmedQuery,
            lemma: token.matched_lemma ?? token.lemma_candidate ?? token.lemma ?? null,
            classification: token.classification,
            translation: resolvedLemma.english_translation ?? null,
            matchedLemma: resolvedLemma,
          })
          return
        }

        let translation: string | null = null
        if (token.classification !== "typo_likely") {
          try {
            const translationResponse = await fetch(`${BACKEND_URL}/api/wordbank/translation`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                surface_token: token.surface_token || trimmedQuery,
                lemma_candidate: token.lemma_candidate ?? token.lemma ?? null,
              }),
              signal: controller.signal,
            })
            if (translationResponse.ok) {
              const translationPayload = (await translationResponse.json()) as GenerateTranslationResponse
              translation = translationPayload.english_translation?.trim() || null
            }
          } catch {
            translation = null
          }
        }

        if (!cancelled) {
          setResolvedQueryCandidate({
            query: normalizedQuery,
            surface: token.surface_token || trimmedQuery,
            lemma: token.lemma_candidate ?? token.lemma ?? null,
            classification: token.classification,
            translation,
            matchedLemma: null,
          })
        }
      } catch {
        if (!cancelled) {
          setResolvedQueryCandidate((current) => (current?.query === normalizedQuery ? null : current))
        }
      }
    })()

    return () => {
      cancelled = true
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
            onValueChange={setSearchQuery}
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
                {newWordResult ? (
                  <CommandItem
                    value={`new-word-${newWordResult.surface} ${newWordResult.lemma} ${newWordResult.translation ?? ""}`}
                    onSelect={() => {
                      void (async () => {
                        const addedLemma = await onAddWordFromSearch(newWordResult.surface, newWordResult.lemma)
                        if (addedLemma) {
                          setIsSearchOpen(false)
                          setSearchQuery("")
                        }
                      })()
                    }}
                    className="flex-col items-start gap-0.5"
                  >
                    <span className="font-medium">Add "{newWordResult.surface}" to wordbank</span>
                    <span className="text-muted-foreground text-xs">
                      Lemma: {newWordResult.lemma}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      {newWordResult.translation?.trim() || "No translation available."}
                    </span>
                  </CommandItem>
                ) : null}
                {addVariationResult ? (
                  <CommandItem
                    value={`add-variation-${addVariationResult.surface} ${addVariationResult.lemma}`}
                    onSelect={() => {
                      void (async () => {
                        const addedLemma = await onAddWordFromSearch(
                          addVariationResult.surface,
                          addVariationResult.lemma,
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
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)

  const [lemmas, setLemmas] = useState<WordbankLemma[]>([])
  const [wordbankError, setWordbankError] = useState<string | null>(null)
  const [isWordbankLoading, setIsWordbankLoading] = useState(false)
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [lemmaDetails, setLemmaDetails] = useState<LemmaDetailsResponse | null>(null)
  const [lemmaDetailsError, setLemmaDetailsError] = useState<string | null>(null)
  const [isLemmaDetailsLoading, setIsLemmaDetailsLoading] = useState(false)
  const [showLemmaDetailsLoadingSkeleton, setShowLemmaDetailsLoadingSkeleton] = useState(false)
  const [isResettingDatabase, setIsResettingDatabase] = useState(false)
  const [selectedNlpModel, setSelectedNlpModel] = useState<NlpModelOption>(
    NLP_MODEL_OPTIONS[0],
  )
  const [highlightPopover, setHighlightPopover] = useState<HighlightPopoverState>({
    open: false,
    left: 0,
    lineTop: 0,
    lineBottom: 0,
    side: "bottom",
    tokenIndex: null,
  })
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

  const latestRequestIdRef = useRef(0)
  const activeControllerRef = useRef<AbortController | null>(null)
  const phraseTranslationRequestKeyRef = useRef<string | null>(null)
  const phraseTranslationDelayTimeoutRef = useRef<number | null>(null)
  const lemmaDetailsLoadingDelayTimeoutRef = useRef<number | null>(null)
  const noteAutosaveTimeoutRef = useRef<number | null>(null)
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
        lemma: popoverToken.lemma ?? rememberedForPos.lemma,
      }
    }

    return {
      ...popoverToken,
      pos_tag: remembered.latest.pos_tag,
      morphology: popoverToken.morphology ?? remembered.latest.morphology,
      lemma_candidate: popoverToken.lemma_candidate ?? remembered.latest.lemma,
      lemma: popoverToken.lemma ?? remembered.latest.lemma,
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
    return popoverDisplayToken.matched_lemma ?? popoverDisplayToken.lemma_candidate ?? popoverDisplayToken.lemma ?? null
  }, [popoverDisplayToken])
  const popoverIsNoun = popoverDisplayToken?.pos_tag === "NOUN"
  const popoverIsVerbLike = popoverDisplayToken?.pos_tag === "VERB" || popoverDisplayToken?.pos_tag === "AUX"
  const activeSavedNote = useMemo(
    () => savedNotes.find((note) => note.id === activeNoteId) ?? null,
    [activeNoteId, savedNotes],
  )
  const activeSavedNoteId = activeSavedNote?.id ?? null
  const activeSavedNoteName = activeSavedNote?.name ?? null
  const popoverLemmaLabel = useMemo(() => {
    if (!popoverLemma) {
      return null
    }
    return lemmaLabelForPos(popoverLemma, popoverDisplayToken?.pos_tag ?? null, popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverDisplayToken?.pos_tag, popoverLemma])
  const showPopoverLemma = Boolean(
    popoverLemmaLabel &&
    popoverDisplayToken &&
    (popoverIsNoun || popoverLemmaLabel !== popoverDisplayToken.surface_token),
  )
  const popoverSecondaryTags = useMemo(() => {
    return secondaryTagsForPos(popoverDisplayToken?.pos_tag ?? null, popoverDisplayToken?.morphology ?? null)
  }, [
    popoverDisplayToken?.morphology,
    popoverDisplayToken?.pos_tag,
  ])
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
        const lemma = token.matched_lemma ?? token.lemma_candidate ?? token.lemma ?? null
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
          const payload = (await response.json()) as { status?: string }
          if (payload.status === "ok") {
            setStatus("connected")
            return
          }
          if (payload.status === "degraded") {
            setStatus("degraded")
            return
          }
          setStatus("offline")
          return
        }
      } catch {
        // ignore and set offline below
      }

      if (!cancelled) {
        setStatus("offline")
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
  }, [activeSection, selectedLemma])

  useEffect(() => {
    if (!highlightPopover.open) {
      return
    }
    if (highlightPopover.tokenIndex === null || !tokens[highlightPopover.tokenIndex]) {
      setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    }
  }, [highlightPopover.open, highlightPopover.tokenIndex, tokens])

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

  async function addWordToWordbank(surfaceToken: string, lemmaCandidate: string | null): Promise<AddWordResponse> {
    const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        surface_token: surfaceToken,
        lemma_candidate: lemmaCandidate,
      }),
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

  async function addTokenToWordbank(token: AnalyzedToken) {
    const requestSurface = token.normalized_token || token.surface_token
    const requestLemma = token.lemma_candidate
    const loadingKey = addLoadingKey(token)

    setAddingTokens((current) => ({ ...current, [loadingKey]: true }))

    try {
      const payload = await addWordToWordbank(requestSurface, requestLemma)
      toast.success(payload.message)
      void postTokenFeedback({
        raw_token: token.surface_token,
        predicted_status: token.classification,
        suggestions_shown: (token.suggestions ?? []).map((item) => item.value),
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
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

  async function addWordFromSearch(surfaceToken: string, lemmaCandidate: string | null): Promise<string | null> {
    try {
      const payload = await addWordToWordbank(surfaceToken, lemmaCandidate)
      toast.success(payload.message)
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
    const sourceWord = token.normalized_token || token.surface_token
    const tokenKeys = translationKeysForToken(token)
    if (tokenKeys.some((key) => Object.hasOwn(generatedTranslationMap, key))) {
      return
    }

    setIsGeneratingTranslation(true)
    setGenerateTranslationError(null)
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/translation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          surface_token: token.surface_token,
          lemma_candidate: token.matched_lemma ?? token.lemma_candidate ?? token.lemma,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Translation request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as GenerateTranslationResponse
      const responseKey = normalizeWordKey(payload.source_word || sourceWord)
      const translation = payload.english_translation?.trim() || null

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

  function openKnownTokenInWordbank(token: AnalyzedToken) {
    const lemma = token.matched_lemma ?? token.lemma_candidate ?? token.lemma
    if (!lemma) {
      return
    }
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    setActiveSection("wordbank")
    setSelectedLemma(lemma)
  }

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
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      setWordbankRefreshTick((current) => current + 1)
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
        <div className="space-y-4">
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
            <ScrollArea className="h-[520px]">
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
                          {lemma.lemma}
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
    const variationForms = lemmaDetails?.surface_forms.filter(
      (form) => form.form.trim().toLocaleLowerCase("da-DK") !== normalizedSelectedLemma,
    ) ?? []
    const lemmaCardLabel = lemmaDetails
      ? lemmaLabelForPos(lemmaDetails.lemma, lemmaDetails.pos_tag, lemmaDetails.morphology)
      : null
    const showLemmaCardLabel = Boolean(
      lemmaDetails &&
      lemmaCardLabel &&
      shouldShowLemmaLabel(lemmaDetails.lemma, lemmaCardLabel, lemmaDetails.pos_tag),
    )

    return (
      <div className="space-y-4">
        {lemmaDetailsError && (
          <p className="text-destructive text-sm" role="alert">
            {lemmaDetailsError}
          </p>
        )}
        {isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton ? (
          <div className="space-y-3">
            <Card>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <Skeleton className="h-6 w-28" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-4 w-32" />
                <div className="flex flex-wrap gap-1.5">
                  <Skeleton className="h-5 w-14 rounded-full" />
                  <Skeleton className="h-5 w-[4.5rem] rounded-full" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
              </CardContent>
            </Card>
            <div className="grid gap-3 md:grid-cols-2">
              <Card>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <Skeleton className="h-6 w-24" />
                    <Skeleton className="h-4 w-16" />
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
          <ScrollArea className="h-[520px]">
            <div className="space-y-3 pr-1">
              <Card>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-lg font-bold leading-tight">{lemmaDetails.lemma}</p>
                    {showLemmaCardLabel ? (
                      <p className="text-muted-foreground text-right text-sm font-normal italic leading-tight">
                        {lemmaCardLabel}
                      </p>
                    ) : null}
                  </div>
                  <p className="text-muted-foreground text-sm">
                    {lemmaDetails.english_translation ?? "No translation available."}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {lemmaDetails.pos_tag && (
                      <Badge variant="secondary" className={posBadgeClass(lemmaDetails.pos_tag)}>
                        {lemmaDetails.pos_tag}
                      </Badge>
                    )}
                    {secondaryTagsForPos(lemmaDetails.pos_tag, lemmaDetails.morphology).map((tag) => (
                      <Badge key={`lemma-tag-${tag}`} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {variationForms.length === 0 ? (
                <p className="text-muted-foreground text-sm">No saved variations for this lemma.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {variationForms.map((form) => {
                    const lemmaLabel = lemmaLabelForPos(lemmaDetails.lemma, form.pos_tag, form.morphology)
                    const showLemmaLabel = shouldShowLemmaLabel(form.form, lemmaLabel, form.pos_tag)
                    return (
                      <Card key={form.form}>
                        <CardContent className="space-y-3">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-lg font-bold leading-tight">{form.form}</p>
                            {showLemmaLabel ? (
                              <p className="text-muted-foreground text-right text-sm font-normal italic leading-tight">
                                {lemmaLabel}
                              </p>
                            ) : null}
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
              className="space-y-2"
            >
              <p className="text-sm font-semibold leading-snug">{phrasePopover.selectedText}</p>
              {isGeneratingPhraseTranslation && !phraseTranslation ? (
                <Skeleton data-testid="phrase-translation-skeleton" className="h-4 w-28" />
              ) : generatePhraseTranslationError ? (
                <p className="text-destructive text-xs">{generatePhraseTranslationError}</p>
              ) : phraseTranslation ? (
                <p className="text-muted-foreground text-sm">{phraseTranslation}</p>
              ) : (
                <p className="text-muted-foreground text-xs">No translation available.</p>
              )}
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
              className="space-y-3"
            >
              {popoverDisplayToken && (
                <>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-3">
                      {popoverDisplayToken.surface_token ? (
                        <p className="text-lg font-bold leading-tight">{popoverDisplayToken.surface_token}</p>
                      ) : (
                        <Skeleton data-testid="word-skeleton" className="h-7 w-28" />
                      )}
                      {showPopoverLemma ? (
                        <p className="text-muted-foreground text-right text-sm font-normal italic leading-tight">
                          {popoverLemmaLabel}
                        </p>
                      ) : (popoverIsNoun || popoverIsVerbLike) && !popoverLemma ? (
                        <Skeleton
                          data-testid={popoverIsNoun ? "noun-lemma-skeleton" : "verb-lemma-skeleton"}
                          className="h-4 w-20"
                        />
                      ) : null}
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
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {popoverDisplayToken.pos_tag && (
                        <Badge variant="secondary" className={posBadgeClass(popoverDisplayToken.pos_tag)}>
                          {popoverDisplayToken.pos_tag}
                        </Badge>
                      )}
                      {popoverSecondaryTags.map((tag) => (
                        <Badge key={tag} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {popoverDisplayToken.classification === "known" ? (
                    <Button
                      type="button"
                      size="sm"
                      className="w-full"
                      disabled={!popoverLemma}
                      onClick={() => {
                        openKnownTokenInWordbank(popoverDisplayToken)
                      }}
                    >
                      Open in wordbank
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      className="w-full"
                      disabled={Boolean(addingTokens[addLoadingKey(popoverDisplayToken)])}
                      onClick={() => {
                        void addTokenToWordbank(popoverDisplayToken)
                        setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
                      }}
                    >
                      {addingTokens[addLoadingKey(popoverDisplayToken)]
                        ? "Adding..."
                        : popoverDisplayToken.classification === "variation"
                          ? "Add variation"
                          : "Add to wordbank"}
                    </Button>
                  )}
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
        <main className="w-full px-1 pt-3 pb-2 md:px-2 md:pt-8 md:pb-4">
          <span className="sr-only" aria-label="backend-connection-status">
            {status}
          </span>
          <div className="mx-auto w-full max-w-7xl">
            <div className="mb-1 md:mb-2 flex items-center justify-between gap-3">
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
                </div>
              ) : null}
            </div>
            {activeSection === "playground"
              ? renderPlaygroundContent()
              : activeSection === "notes"
                ? renderNotesContent()
              : activeSection === "wordbank"
                ? renderWordbankContent()
                : renderDeveloperContent()}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
