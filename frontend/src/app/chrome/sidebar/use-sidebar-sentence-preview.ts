import { useEffect, useRef, useState } from "react"

import {
  SENTENCE_DEBOUNCE_DA_MS,
  SENTENCE_DEBOUNCE_EN_MS,
  type SentenceSearchPreviewResponse,
} from "@/app/core"
import { detectQueryLanguage } from "@/app/chrome/sidebar/sidebar-search-query"
import type { SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

export function useSidebarSentencePreview({
  apiClient,
  isSentenceMode,
  sentenceQuery,
  resetVersion,
}: {
  apiClient: SidebarApiClient
  isSentenceMode: boolean
  sentenceQuery: string
  resetVersion: string
}) {
  const cacheRef = useRef<Map<string, SentenceSearchPreviewResponse>>(new Map())
  const [sentenceSearchPreview, setSentenceSearchPreview] = useState<{
    query: string
    result: SentenceSearchPreviewResponse
  } | null>(null)
  const [isSentenceSearchPreviewLoading, setIsSentenceSearchPreviewLoading] = useState(false)
  const [sentenceSearchPreviewError, setSentenceSearchPreviewError] = useState<string | null>(null)

  useEffect(() => {
    cacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setSentenceSearchPreview(null)
      setSentenceSearchPreviewError(null)
      setIsSentenceSearchPreviewLoading(false)
    }, 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    if (!isSentenceMode || !sentenceQuery) {
      const clearId = window.setTimeout(() => {
        setSentenceSearchPreview(null)
        setSentenceSearchPreviewError(null)
        setIsSentenceSearchPreviewLoading(false)
      }, 0)
      return () => window.clearTimeout(clearId)
    }

    const cached = cacheRef.current.get(sentenceQuery)
    if (cached) {
      const clearId = window.setTimeout(() => {
        setSentenceSearchPreview({ query: sentenceQuery, result: cached })
        setIsSentenceSearchPreviewLoading(false)
        setSentenceSearchPreviewError(null)
      }, 0)
      return () => window.clearTimeout(clearId)
    }

    let cancelled = false
    let gotFullResult = false
    const initId = window.setTimeout(() => {
      if (!cancelled) {
        setSentenceSearchPreview(null)
        setIsSentenceSearchPreviewLoading(true)
        setSentenceSearchPreviewError(null)
      }
    }, 0)
    const detectedLang = detectQueryLanguage(sentenceQuery)
    const debounceMs = detectedLang === "da" ? SENTENCE_DEBOUNCE_DA_MS : SENTENCE_DEBOUNCE_EN_MS

    const timeoutId = window.setTimeout(() => {
      const fastPromise = apiClient.postJson<SentenceSearchPreviewResponse>(
        "/api/sentencebank/search-preview",
        { source_text: sentenceQuery, fast: true },
        "Could not prepare sentence preview.",
      )
      const fullPromise = apiClient.postJson<SentenceSearchPreviewResponse>(
        "/api/sentencebank/search-preview",
        { source_text: sentenceQuery, fast: false },
        "Could not prepare sentence preview.",
      )

      void fastPromise
        .then((fastResult) => {
          if (!cancelled && !gotFullResult) {
            setSentenceSearchPreview({ query: sentenceQuery, result: fastResult })
          }
        })
        .catch(() => {})

      void fullPromise
        .then((fullResult) => {
          if (cancelled) return
          gotFullResult = true
          cacheRef.current.set(sentenceQuery, fullResult)
          setSentenceSearchPreview({ query: sentenceQuery, result: fullResult })
          setSentenceSearchPreviewError(null)
        })
        .catch((error) => {
          if (cancelled) return
          gotFullResult = true
          const fallback: SentenceSearchPreviewResponse = {
            status: "ready",
            query_language: "unknown",
            source_text: sentenceQuery,
            english_translation: null,
            message: null,
            is_valid: true,
            errors: [],
          }
          setSentenceSearchPreviewError(
            error instanceof Error ? error.message : "Could not prepare sentence preview.",
          )
          setSentenceSearchPreview({ query: sentenceQuery, result: fallback })
        })
        .finally(() => {
          if (!cancelled) {
            setIsSentenceSearchPreviewLoading(false)
          }
        })
    }, debounceMs)

    return () => {
      cancelled = true
      window.clearTimeout(initId)
      window.clearTimeout(timeoutId)
      setIsSentenceSearchPreviewLoading(false)
    }
  }, [apiClient, isSentenceMode, sentenceQuery, resetVersion])

  const activeSentenceSearchPreview = sentenceSearchPreview?.query === sentenceQuery
    ? sentenceSearchPreview.result
    : null

  return {
    sentenceSearchPreview: activeSentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    sentenceSearchPreviewError,
  }
}
