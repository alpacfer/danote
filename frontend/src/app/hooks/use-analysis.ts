import { useEffect, useMemo, useRef, useState } from "react"

import {
  ANALYZE_DEBOUNCE_MS,
  finalizedAnalysisText,
  type AnalyzedToken,
} from "@/app/core"
import { mapAnalyzedTokensToHighlights } from "@/lib/token-highlights"

type UseAnalysisParams = {
  noteText: string
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
}

export function useAnalysis({
  noteText,
  backendUrl,
  extractErrorMessage,
}: UseAnalysisParams) {
  const [tokens, setTokens] = useState<AnalyzedToken[]>([])
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisRefreshTick, setAnalysisRefreshTick] = useState(0)

  const latestRequestIdRef = useRef(0)
  const activeControllerRef = useRef<AbortController | null>(null)

  const analysisInput = useMemo(() => finalizedAnalysisText(noteText), [noteText])
  const noteHighlights = useMemo(
    () => mapAnalyzedTokensToHighlights(noteText, tokens),
    [noteText, tokens],
  )

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
        const response = await fetch(`${backendUrl}/api/analyze`, {
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
      }
    }, ANALYZE_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [analysisInput, analysisRefreshTick, backendUrl, extractErrorMessage])

  useEffect(() => {
    return () => {
      activeControllerRef.current?.abort()
    }
  }, [])

  return {
    tokens,
    setTokens,
    analysisError,
    setAnalysisError,
    analysisRefreshTick,
    setAnalysisRefreshTick,
    noteHighlights,
  }
}
