import { useEffect, useMemo, useRef, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"

type ConnectionStatus = "loading" | "connected" | "degraded" | "offline"
type TokenClassification = "known" | "variation" | "new"

type AnalyzedToken = {
  surface_token: string
  normalized_token: string
  lemma_candidate: string | null
  classification: TokenClassification
  match_source: "exact" | "lemma" | "none"
  matched_lemma: string | null
  matched_surface_form: string | null
}

type AddWordResponse = {
  status: "inserted" | "exists"
  stored_lemma: string
  stored_surface_form: string | null
  source: "manual"
  message: string
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

function App() {
  const [status, setStatus] = useState<ConnectionStatus>("loading")
  const [noteText, setNoteText] = useState("")
  const [tokens, setTokens] = useState<AnalyzedToken[]>([])
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisRefreshTick, setAnalysisRefreshTick] = useState(0)
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const latestRequestIdRef = useRef(0)
  const activeControllerRef = useRef<AbortController | null>(null)
  const analysisInput = useMemo(() => finalizedAnalysisText(noteText), [noteText])

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
    const loadingKey = requestSurface

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
      setAnalysisRefreshTick((current) => current + 1)
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

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl p-6 md:p-8">
      <Card className="min-h-[75vh]">
        <CardHeader className="gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Danote</CardTitle>
              <CardDescription>Language-learning notes with Danish-first analysis.</CardDescription>
            </div>
            <Badge variant={badgeVariant} aria-label="backend-connection-status">
              {status}
            </Badge>
          </div>
          <Separator />
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="notes" className="w-full gap-4">
            <TabsList>
              <TabsTrigger value="notes">Notes</TabsTrigger>
              <TabsTrigger value="detected-words">Detected words</TabsTrigger>
            </TabsList>

            <TabsContent value="notes">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Lesson Notes</CardTitle>
                  <CardDescription>
                    Write naturally. Analysis results will appear in the detected words tab.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="lesson-notes">Notes text</Label>
                  <p className="text-muted-foreground text-sm">
                      Paste or type your lesson notes here. Analysis runs after a pause and only includes finalized
                      tokens.
                  </p>
                    <Textarea
                      id="lesson-notes"
                      placeholder="Type lesson notes here..."
                      className="min-h-[360px] resize-y"
                      value={noteText}
                      onChange={(event) => setNoteText(event.target.value)}
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-muted-foreground text-sm">Legend:</span>
                    <Badge variant="secondary">known</Badge>
                    <Badge variant="outline">variation</Badge>
                    <Badge variant="destructive">new</Badge>
                  </div>
                  <p className="text-muted-foreground text-xs">
                    Auto-analysis uses a short debounce and processes the full note text.
                  </p>
                  {analysisError && (
                    <p className="text-destructive text-sm" role="alert">
                      {analysisError}
                    </p>
                  )}
                  <p className="text-muted-foreground text-xs" aria-label="note-character-count">
                    Characters: {noteText.length}
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="detected-words">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Detected Words</CardTitle>
                  <CardDescription>
                    Results from the last Analyze request.
                  </CardDescription>
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
                          tokens.map((token, index) => (
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
                                {token.classification === "new" ? (
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="xs"
                                    disabled={Boolean(addingTokens[token.normalized_token])}
                                    onClick={() => {
                                      void addTokenToWordbank(token)
                                    }}
                                  >
                                    {addingTokens[token.normalized_token] ? "Adding..." : "Add"}
                                  </Button>
                                ) : (
                                  <span className="text-muted-foreground text-xs">-</span>
                                )}
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </main>
  )
}

export default App
