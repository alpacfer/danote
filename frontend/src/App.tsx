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
  x: number
  y: number
  tokenIndex: number | null
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
const ANALYZE_DEBOUNCE_MS = 450

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
  const [highlightPopover, setHighlightPopover] = useState<HighlightPopoverState>({
    open: false,
    x: 0,
    y: 0,
    tokenIndex: null,
  })
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
  const popoverTranslation = useMemo(() => {
    if (!popoverToken) {
      return null
    }
    const key = normalizeWordKey(popoverToken.normalized_token || popoverToken.surface_token)
    return generatedTranslationMap[key] ?? null
  }, [generatedTranslationMap, popoverToken])

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
    const sourceKey = normalizeWordKey(sourceWord)
    if (Object.hasOwn(generatedTranslationMap, sourceKey)) {
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

      setGeneratedTranslationMap((current) => ({ ...current, [responseKey]: translation }))
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate translation."
      setGenerateTranslationError(message)
      void error
    } finally {
      setIsGeneratingTranslation(false)
    }
  }

  function openHighlightPopover(tokenIndex: number, x: number, y: number) {
    setHighlightPopover({ open: true, tokenIndex, x, y })
    const token = tokens[tokenIndex]
    if (token) {
      void generateTranslationForToken(token)
    }
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
                open={highlightPopover.open && Boolean(popoverToken)}
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
                    style={{ left: highlightPopover.x, top: highlightPopover.y }}
                  />
                </PopoverAnchor>
                <PopoverContent align="start" sideOffset={8} className="space-y-3">
                  {popoverToken && (
                    <>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">{popoverToken.surface_token}</p>
                        <p className="text-muted-foreground text-xs">
                          {popoverToken.classification === "variation" ? "variation" : "word"}
                        </p>
                        {popoverToken.pos_tag && (
                          <p className="text-muted-foreground text-xs">POS: {popoverToken.pos_tag}</p>
                        )}
                        {popoverToken.morphology && (
                          <p className="text-muted-foreground text-xs">Morphology: {popoverToken.morphology}</p>
                        )}
                      </div>

                      <div className="space-y-1">
                        <p className="text-xs font-medium">Translations</p>
                        {isGeneratingTranslation ? (
                          <p className="text-muted-foreground text-xs">Loading translations...</p>
                        ) : generateTranslationError ? (
                          <p className="text-destructive text-xs">
                            {generateTranslationError}
                          </p>
                        ) : popoverTranslation ? (
                          <ul className="text-muted-foreground list-disc pl-4 text-xs">
                            <li>{popoverTranslation}</li>
                          </ul>
                        ) : (
                          <p className="text-muted-foreground text-xs">No translation available.</p>
                        )}
                      </div>

                      <Button
                        type="button"
                        size="sm"
                        className="w-full"
                        disabled={Boolean(addingTokens[addLoadingKey(popoverToken)])}
                        onClick={() => {
                          void addTokenToWordbank(popoverToken)
                          setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
                        }}
                      >
                        {addingTokens[addLoadingKey(popoverToken)]
                          ? "Adding..."
                          : popoverToken.classification === "variation"
                            ? "Add variation"
                            : "Add to wordbank"}
                      </Button>
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
                onHighlightClick={({ tokenIndex, x, y }) => {
                  openHighlightPopover(tokenIndex, x, y)
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
