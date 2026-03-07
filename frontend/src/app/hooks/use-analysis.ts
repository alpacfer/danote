import { useEffect, useMemo, useRef, useState } from "react"

import {
  ANALYZE_DEBOUNCE_MS,
  createApiClient,
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
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  useEffect(() => {
    if (!analysisInput) {
      activeControllerRef.current?.abort()
      const clearId = window.setTimeout(() => {
        setAnalysisError(null)
        setTokens([])
      }, 0)
      return () => {
        window.clearTimeout(clearId)
      }
    }

    const timeoutId = window.setTimeout(async () => {
      const requestId = latestRequestIdRef.current + 1
      latestRequestIdRef.current = requestId

      activeControllerRef.current?.abort()
      const controller = new AbortController()
      activeControllerRef.current = controller

      setAnalysisError(null)
      try {
        const payload = await apiClient.postJson<{ tokens: AnalyzedToken[] }>(
          "/api/analyze",
          { text: analysisInput },
          "Could not analyze notes.",
          {
            signal: controller.signal,
          },
        )

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
  }, [analysisInput, analysisRefreshTick, apiClient])

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
