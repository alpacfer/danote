import { useEffect, useMemo, useRef, useState } from "react"
import { ArrowLeft, BookOpen, Moon, NotebookPen, Settings, Sun } from "lucide-react"
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
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { NotesEditor } from "@/components/notes-editor"
import { mapAnalyzedTokensToHighlights } from "@/lib/token-highlights"
import { toast } from "sonner"

type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
type TokenClassification = "known" | "variation" | "typo_likely" | "uncertain" | "new"
type AppSection = "playground" | "wordbank" | "developer"
type TokenAction = "replace" | "add_as_new" | "ignore" | "dismiss"

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
  surface_forms: Array<{
    form: string
    english_translation: string | null
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

type DiscoveredTokenMetadata = {
  pos_tag: string
  morphology: string | null
  lemma: string | null
}

type DiscoveredTokenMemory = {
  latest: DiscoveredTokenMetadata
  byPos: Record<string, DiscoveredTokenMetadata>
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
const ANALYZE_DEBOUNCE_MS = 450
const NLP_MODEL_OPTIONS = [
  "da_dacy_small_trf-0.2.0",
  "da_dacy_medium_trf-0.2.0",
  "da_dacy_large_trf-0.2.0",
] as const
const POPOVER_VIEWPORT_MARGIN_PX = 12
const POPOVER_ESTIMATED_HEIGHT_PX = 280

type NlpModelOption = (typeof NLP_MODEL_OPTIONS)[number]

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

function escapeRegex(input: string): string {
  return input.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function replaceFirstTokenOccurrence(text: string, source: string, replacement: string): string {
  if (!source) {
    return text
  }
  const pattern = new RegExp(`\\b${escapeRegex(source)}\\b`, "u")
  if (pattern.test(text)) {
    return text.replace(pattern, replacement)
  }
  return text.replace(source, replacement)
}

function normalizeWordKey(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase()
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

function isLowConfidencePosTag(posTag: string | null): boolean {
  return !posTag || posTag === "X"
}

function translationKeysForToken(token: Pick<AnalyzedToken, "surface_token" | "normalized_token" | "matched_lemma" | "lemma_candidate" | "lemma">): string[] {
  const keys = [
    token.normalized_token,
    token.surface_token,
    token.matched_lemma,
    token.lemma_candidate,
    token.lemma,
  ]
    .filter((value): value is string => Boolean(value && value.trim()))
    .map((value) => normalizeWordKey(value))

  return [...new Set(keys)]
}

type AppSidebarProps = {
  activeSection: AppSection
  onSelectPlayground: () => void
  onSelectWordbank: () => void
  onSelectDeveloper: () => void
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
  onSelectWordbank: () => void
}

function AppBreadcrumb({
  activeSection,
  selectedLemma,
  onSelectWordbank,
}: AppBreadcrumbProps) {
  if (activeSection === "playground") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl font-semibold">
          <BreadcrumbItem>
            <BreadcrumbPage>Playground</BreadcrumbPage>
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
  onSelectPlayground,
  onSelectWordbank,
  onSelectDeveloper,
}: AppSidebarProps) {
  return (
    <Sidebar variant="inset">
      <SidebarHeader>
        <p className="px-2 text-sm font-semibold">Danote</p>
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
  const [tokens, setTokens] = useState<AnalyzedToken[]>([])
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisRefreshTick, setAnalysisRefreshTick] = useState(0)
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const [ignoringTokens, setIgnoringTokens] = useState<Record<string, boolean>>({})
  const [replacingTokens, setReplacingTokens] = useState<Record<string, boolean>>({})
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)

  const [lemmas, setLemmas] = useState<WordbankLemma[]>([])
  const [wordbankError, setWordbankError] = useState<string | null>(null)
  const [isWordbankLoading, setIsWordbankLoading] = useState(false)
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [lemmaDetails, setLemmaDetails] = useState<LemmaDetailsResponse | null>(null)
  const [lemmaDetailsError, setLemmaDetailsError] = useState<string | null>(null)
  const [isLemmaDetailsLoading, setIsLemmaDetailsLoading] = useState(false)
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
  const [discoveredTokenMetadata, setDiscoveredTokenMetadata] = useState<Record<string, DiscoveredTokenMemory>>({})
  const [generatedTranslationMap, setGeneratedTranslationMap] = useState<Record<string, string | null>>({})
  const [isGeneratingTranslation, setIsGeneratingTranslation] = useState(false)
  const [generateTranslationError, setGenerateTranslationError] = useState<string | null>(null)

  const latestRequestIdRef = useRef(0)
  const activeControllerRef = useRef<AbortController | null>(null)
  const analysisInput = useMemo(() => finalizedAnalysisText(noteText), [noteText])
  const noteHighlights = useMemo(
    () => mapAnalyzedTokensToHighlights(noteText, tokens),
    [noteText, tokens],
  )
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
  const popoverIsAdj = popoverDisplayToken?.pos_tag === "ADJ"
  const popoverIsDet = popoverDisplayToken?.pos_tag === "DET"
  const popoverIsPron = popoverDisplayToken?.pos_tag === "PRON"
  const popoverIsAdv = popoverDisplayToken?.pos_tag === "ADV"
  const showNounLemma =
    popoverIsNoun &&
    Boolean(popoverLemma)
  const popoverNounArticle = useMemo(() => {
    if (!popoverIsNoun) {
      return null
    }
    return nounArticleFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsNoun])
  const popoverNounNumber = useMemo(() => {
    if (!popoverIsNoun) {
      return null
    }
    return numberFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsNoun])
  const popoverVerbForm = useMemo(() => {
    if (!popoverIsVerbLike) {
      return null
    }
    return verbFormFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsVerbLike])
  const popoverAdjGender = useMemo(() => {
    if (!popoverIsAdj) {
      return null
    }
    return genderFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsAdj])
  const popoverAdjNumber = useMemo(() => {
    if (!popoverIsAdj) {
      return null
    }
    return numberFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsAdj])
  const popoverDetGender = useMemo(() => {
    if (!popoverIsDet) {
      return null
    }
    return genderFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsDet])
  const popoverDetNumber = useMemo(() => {
    if (!popoverIsDet) {
      return null
    }
    return numberFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsDet])
  const popoverPronPerson = useMemo(() => {
    if (!popoverIsPron) {
      return null
    }
    return personFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsPron])
  const popoverPronNumber = useMemo(() => {
    if (!popoverIsPron) {
      return null
    }
    return numberFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsPron])
  const popoverAdvDegree = useMemo(() => {
    if (!popoverIsAdv) {
      return null
    }
    return degreeFromMorphology(popoverDisplayToken?.morphology ?? null)
  }, [popoverDisplayToken?.morphology, popoverIsAdv])
  const showTranslationSkeleton = isGeneratingTranslation || (
    (popoverIsNoun || popoverIsVerbLike) &&
    (!popoverTranslation || Boolean(generateTranslationError))
  )

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
      setIsAnalyzing(false)
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

      setIsAnalyzing(true)
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
      } finally {
        if (requestId === latestRequestIdRef.current) {
          setIsAnalyzing(false)
        }
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
    if (activeSection !== "wordbank") {
      return
    }

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
  }, [activeSection, wordbankRefreshTick])

  useEffect(() => {
    if (activeSection !== "wordbank" || !selectedLemma) {
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      setIsLemmaDetailsLoading(false)
      return
    }

    let cancelled = false
    setIsLemmaDetailsLoading(true)
    setLemmaDetailsError(null)

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
        if (!cancelled) {
          setIsLemmaDetailsLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
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

  const statusVariantMap: Record<TokenClassification, "secondary" | "outline" | "destructive"> = {
    known: "secondary",
    variation: "outline",
    typo_likely: "destructive",
    uncertain: "outline",
    new: "destructive",
  }
  const sourceVariantMap: Record<AnalyzedToken["match_source"], "secondary" | "outline" | "destructive"> = {
    exact: "secondary",
    lemma: "outline",
    none: "destructive",
  }

  async function addTokenToWordbank(token: AnalyzedToken) {
    const requestSurface = token.normalized_token || token.surface_token
    const requestLemma = token.lemma_candidate
    const loadingKey = addLoadingKey(token)

    setAddingTokens((current) => ({ ...current, [loadingKey]: true }))

    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/lexemes`, {
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
          `Add word request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as AddWordResponse
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
      const lemmaKey = normalizeWordKey(payload.lemma || "")
      const translation = payload.english_translation?.trim() || null

      setGeneratedTranslationMap((current) => {
        const next = { ...current }
        for (const key of [...tokenKeys, responseKey, lemmaKey]) {
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

  function openHighlightPopover(tokenIndex: number, left: number, lineTop: number, lineBottom: number) {
    const token = tokens[tokenIndex]
    if (!token || token.classification === "typo_likely" || token.pos_tag === "PROPN" || token.pos_tag === "NUM") {
      return
    }

    const side = preferredPopoverSide(lineTop, lineBottom)
    setHighlightPopover({ open: true, tokenIndex, left, lineTop, lineBottom, side })
    void generateTranslationForToken(token)
  }

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

  async function ignoreToken(token: AnalyzedToken) {
    const loadingKey = addLoadingKey(token)
    setIgnoringTokens((current) => ({ ...current, [loadingKey]: true }))
    try {
      const response = await fetch(`${BACKEND_URL}/api/tokens/ignore`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: token.normalized_token || token.surface_token, scope: "global" }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Ignore token request failed with status ${response.status}`,
        )
        throw new Error(message)
      }
      void postTokenFeedback({
        raw_token: token.surface_token,
        predicted_status: token.classification,
        suggestions_shown: (token.suggestions ?? []).map((item) => item.value),
        user_action: "ignore",
      })
      toast.success(`Ignoring "${token.surface_token}" for typo checks.`)
      setAnalysisRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not ignore token."
      toast.error(message)
      void error
    } finally {
      setIgnoringTokens((current) => {
        const next = { ...current }
        delete next[loadingKey]
        return next
      })
    }
  }

  async function replaceTokenWithSuggestion(token: AnalyzedToken) {
    const topSuggestion = token.suggestions?.[0]?.value
    if (!topSuggestion) {
      return
    }
    const loadingKey = addLoadingKey(token)
    setReplacingTokens((current) => ({ ...current, [loadingKey]: true }))
    try {
      setNoteText((current) => replaceFirstTokenOccurrence(current, token.surface_token, topSuggestion))
      void postTokenFeedback({
        raw_token: token.surface_token,
        predicted_status: token.classification,
        suggestions_shown: (token.suggestions ?? []).map((item) => item.value),
        user_action: "replace",
        chosen_value: topSuggestion,
      })
      toast.success(`Replaced "${token.surface_token}" with "${topSuggestion}".`)
    } finally {
      setReplacingTokens((current) => {
        const next = { ...current }
        delete next[loadingKey]
        return next
      })
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

  function renderWordbankContent() {
    if (!selectedLemma) {
      return (
        <div className="space-y-4">
          {wordbankError && (
            <p className="text-destructive text-sm" role="alert">
              {wordbankError}
            </p>
          )}
          {isWordbankLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : lemmas.length === 0 ? (
            <p className="text-muted-foreground text-sm">No saved lemmas yet.</p>
          ) : (
            <ScrollArea className="h-[520px]">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {lemmas.map((lemma) => (
                  <Button
                    key={lemma.lemma}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-9 justify-center"
                    onClick={() => setSelectedLemma(lemma.lemma)}
                  >
                    {lemma.lemma}
                    {lemma.english_translation ? ` (${lemma.english_translation})` : ""}
                  </Button>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">
            {lemmaDetails?.lemma ?? selectedLemma}
            {lemmaDetails?.english_translation
              ? ` (${lemmaDetails.english_translation})`
              : ""}
          </h2>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSelectedLemma(null)
            }}
          >
            <ArrowLeft className="size-4" />
            Back to list
          </Button>
        </div>
        <Separator />
        {lemmaDetailsError && (
          <p className="text-destructive text-sm" role="alert">
            {lemmaDetailsError}
          </p>
        )}
        {isLemmaDetailsLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : !lemmaDetails ? (
          <p className="text-muted-foreground text-sm">No details found for this lemma.</p>
        ) : lemmaDetails.surface_forms.length === 0 ? (
          <p className="text-muted-foreground text-sm">No saved variations for this lemma.</p>
        ) : (
          <ScrollArea className="h-[520px] rounded-md border p-2">
            <div className="divide-border divide-y rounded-md border">
              {lemmaDetails.surface_forms.map((form) => (
                <div key={form.form} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                  <span>{form.form}</span>
                  <span className="text-muted-foreground text-xs">{form.english_translation ?? "No translation"}</span>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    )
  }

  function renderPlaygroundContent() {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Lesson Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative">
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
                <PopoverContent side={highlightPopover.side} align="start" sideOffset={8} className="space-y-3">
                  {popoverDisplayToken && (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          {popoverDisplayToken.surface_token ? (
                            <p className="text-lg font-semibold leading-tight">
                              {popoverDisplayToken.surface_token}
                              {popoverIsNoun && popoverNounNumber && (
                                <span className="text-muted-foreground ml-2 text-sm font-normal italic">
                                  {popoverNounNumber}
                                </span>
                              )}
                              {popoverIsVerbLike && popoverVerbForm && (
                                <span className="text-muted-foreground ml-2 text-sm font-normal italic">
                                  {popoverVerbForm}
                                </span>
                              )}
                            </p>
                          ) : (
                            <Skeleton data-testid="word-skeleton" className="h-7 w-28" />
                          )}
                          {popoverIsNoun ? (
                            showNounLemma && popoverLemma ? (
                              <p className="text-muted-foreground text-sm">
                                {popoverNounArticle ? `${popoverLemma} (${popoverNounArticle})` : popoverLemma}
                              </p>
                            ) : !popoverLemma ? (
                              <Skeleton data-testid="noun-lemma-skeleton" className="h-4 w-20" />
                            ) : null
                          ) : popoverIsVerbLike ? (
                            popoverLemma ? (
                              <p className="text-muted-foreground text-sm">{`at ${popoverLemma}`}</p>
                            ) : (
                              <Skeleton data-testid="verb-lemma-skeleton" className="h-4 w-20" />
                            )
                          ) : popoverLemma && popoverLemma !== popoverDisplayToken.surface_token ? (
                            <p className="text-muted-foreground text-sm">{popoverLemma}</p>
                          ) : null}
                        </div>
                        {popoverDisplayToken.pos_tag && (
                          <Badge variant="secondary" className={posBadgeClass(popoverDisplayToken.pos_tag)}>
                            {popoverDisplayToken.pos_tag}
                          </Badge>
                        )}
                      </div>

                      {(popoverIsAdj || popoverIsDet || popoverIsPron || popoverIsAdv) && (
                        <div className="space-y-1">
                          {popoverIsAdj && popoverAdjGender && (
                            <p className="text-muted-foreground text-xs">Gender: {popoverAdjGender}</p>
                          )}
                          {popoverIsAdj && popoverAdjNumber && (
                            <p className="text-muted-foreground text-xs">Number: {popoverAdjNumber}</p>
                          )}
                          {popoverIsDet && popoverDetGender && (
                            <p className="text-muted-foreground text-xs">Gender: {popoverDetGender}</p>
                          )}
                          {popoverIsDet && popoverDetNumber && (
                            <p className="text-muted-foreground text-xs">Number: {popoverDetNumber}</p>
                          )}
                          {popoverIsPron && popoverPronPerson && (
                            <p className="text-muted-foreground text-xs">Person: {popoverPronPerson}</p>
                          )}
                          {popoverIsPron && popoverPronNumber && (
                            <p className="text-muted-foreground text-xs">Number: {popoverPronNumber}</p>
                          )}
                          {popoverIsAdv && popoverAdvDegree && (
                            <p className="text-muted-foreground text-xs">Degree: {popoverAdvDegree}</p>
                          )}
                        </div>
                      )}

                      <div className="space-y-1">
                        <p className="text-xs font-medium">Translation</p>
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
                onChange={setNoteText}
                onHighlightClick={({ tokenIndex, left, lineTop, lineBottom }) => {
                  openHighlightPopover(tokenIndex, left, lineTop, lineBottom)
                }}
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
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detected Words</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[320px] w-full rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Token</TableHead>
                    <TableHead>Lemma</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Match source</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isAnalyzing ? (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <div className="space-y-2">
                          <p className="text-muted-foreground text-sm">Loading detected words...</p>
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-4/5" />
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : analysisError ? (
                    <TableRow>
                      <TableCell className="text-destructive" colSpan={5}>
                        Could not load detected words. Try analyzing again.
                      </TableCell>
                    </TableRow>
                  ) : tokens.length === 0 ? (
                    <TableRow>
                      <TableCell className="text-muted-foreground">No tokens yet</TableCell>
                      <TableCell className="text-muted-foreground">-</TableCell>
                      <TableCell>
                        <Badge variant="outline">pending</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">-</TableCell>
                      <TableCell className="text-muted-foreground">-</TableCell>
                    </TableRow>
                  ) : (
                    tokens.map((token, index) => {
                      const loadingKey = addLoadingKey(token)
                      return (
                        <TableRow key={`${token.surface_token}-${token.match_source}-${index}`}>
                          <TableCell>{token.surface_token}</TableCell>
                          <TableCell>{token.matched_lemma ?? token.lemma_candidate ?? "-"}</TableCell>
                          <TableCell>
                            <Badge variant={statusVariantMap[token.classification]}>
                              {token.classification}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={sourceVariantMap[token.match_source]}>
                              {token.match_source}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {token.classification === "new" && (
                              <Button
                                type="button"
                                variant="outline"
                                size="xs"
                                disabled={Boolean(addingTokens[loadingKey])}
                                onClick={() => {
                                  void addTokenToWordbank(token)
                                }}
                              >
                                {addingTokens[loadingKey] ? "Adding..." : "Add"}
                              </Button>
                            )}
                            {token.classification === "typo_likely" && (
                              <div className="flex flex-wrap gap-1">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="xs"
                                  disabled={Boolean(replacingTokens[loadingKey]) || !token.suggestions?.[0]}
                                  onClick={() => {
                                    void replaceTokenWithSuggestion(token)
                                  }}
                                >
                                  {replacingTokens[loadingKey] ? "Replacing..." : "Replace"}
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="xs"
                                  disabled={Boolean(addingTokens[loadingKey])}
                                  onClick={() => {
                                    void addTokenToWordbank(token)
                                  }}
                                >
                                  {addingTokens[loadingKey] ? "Adding..." : "Add"}
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="xs"
                                  disabled={Boolean(ignoringTokens[loadingKey])}
                                  onClick={() => {
                                    void ignoreToken(token)
                                  }}
                                >
                                  {ignoringTokens[loadingKey] ? "Ignoring..." : "Ignore"}
                                </Button>
                              </div>
                            )}
                            {token.classification === "uncertain" && (
                              <div className="flex flex-wrap gap-1">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="xs"
                                  disabled={Boolean(addingTokens[loadingKey])}
                                  onClick={() => {
                                    void addTokenToWordbank(token)
                                  }}
                                >
                                  {addingTokens[loadingKey] ? "Adding..." : "Add"}
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="xs"
                                  disabled={Boolean(ignoringTokens[loadingKey])}
                                  onClick={() => {
                                    void ignoreToken(token)
                                  }}
                                >
                                  {ignoringTokens[loadingKey] ? "Ignoring..." : "Ignore"}
                                </Button>
                              </div>
                            )}
                            {token.classification !== "new" &&
                              token.classification !== "typo_likely" &&
                              token.classification !== "uncertain" && (
                              <span className="text-muted-foreground text-xs">-</span>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
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
        onSelectPlayground={() => {
          setActiveSection("playground")
        }}
        onSelectWordbank={() => {
          setActiveSection("wordbank")
          setSelectedLemma(null)
        }}
        onSelectDeveloper={() => {
          setActiveSection("developer")
          setSelectedLemma(null)
        }}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger />
          <span className="text-sm font-medium">Danote</span>
        </header>
        <main className="w-full p-4 md:p-8">
          <span className="sr-only" aria-label="backend-connection-status">
            {status}
          </span>
          <div className="mb-4 flex justify-start">
            <AppBreadcrumb
              activeSection={activeSection}
              selectedLemma={selectedLemma}
              onSelectWordbank={() => {
                setActiveSection("wordbank")
                setSelectedLemma(null)
              }}
            />
          </div>
          <div className="mx-auto w-full max-w-7xl">
            {activeSection === "playground"
              ? renderPlaygroundContent()
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
