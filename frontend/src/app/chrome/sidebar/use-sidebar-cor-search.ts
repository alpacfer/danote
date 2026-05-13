import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import {
  SEARCH_RESOLVE_DEBOUNCE_MS,
  isShortLetterWord,
  type CORSearchFormResponse,
} from "@/app/core"
import { getPronounCategory } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { getQuestionWordEntry } from "@/app/sections/wordbank/question-words/question-words-data"
import { hasExactCorFormMatch } from "@/app/chrome/sidebar/sidebar-search-query"
import type { CorFormSearchResult, SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

export function useSidebarCorSearch({
  apiClient,
  shouldSkipLookup,
  normalizedQuery,
  resetVersion,
}: {
  apiClient: SidebarApiClient
  shouldSkipLookup: boolean
  normalizedQuery: string
  resetVersion: string
}) {
  const cacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const [corDidYouMean, setCorDidYouMean] = useState<string | null>(null)
  const [corFormSearchResult, setCorFormSearchResult] = useState<CorFormSearchResult | null>(null)
  const [isCorLookupLoading, setIsCorLookupLoading] = useState(false)
  const [isCorTranslationsLoading, setIsCorTranslationsLoading] = useState(false)

  useEffect(() => {
    cacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setCorFormSearchResult(null)
      setCorDidYouMean(null)
      setIsCorLookupLoading(false)
      setIsCorTranslationsLoading(false)
    }, 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    if (
      shouldSkipLookup
      || !normalizedQuery
      || /\s/u.test(normalizedQuery)
      || isShortLetterWord(normalizedQuery)
      || getQuestionWordEntry(normalizedQuery)
      || getPronounCategory(normalizedQuery)
    ) {
      setIsCorLookupLoading(false)
      setIsCorTranslationsLoading(false)
      setCorDidYouMean(null)
      setCorFormSearchResult(null)
      return
    }

    const cachedPayload = cacheRef.current.get(normalizedQuery)
    if (cachedPayload) {
      setCorFormSearchResult({ query: normalizedQuery, payload: cachedPayload })
      const cachedExact = hasExactCorFormMatch(cachedPayload.groups ?? [], normalizedQuery)
      setCorDidYouMean(cachedExact ? null : (cachedPayload.did_you_mean ?? null))
      setIsCorLookupLoading(false)
      setIsCorTranslationsLoading(false)
      return
    }

    const controller = new AbortController()
    let cancelled = false
    setIsCorLookupLoading(true)
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const partialPayload = await apiClient.tryGetJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(normalizedQuery)}&limit=100&include_translations=false`,
            { signal: controller.signal },
          )
          if (cancelled) return
          if (partialPayload) {
            setCorFormSearchResult({ query: normalizedQuery, payload: partialPayload })
            setIsCorTranslationsLoading(true)
            const partialExact = hasExactCorFormMatch(partialPayload.groups ?? [], normalizedQuery)
            setCorDidYouMean(partialExact ? null : (partialPayload.did_you_mean ?? null))
          }

          const fullPayload = await apiClient.getJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(normalizedQuery)}&limit=100`,
            "Search translation is unavailable.",
            { signal: controller.signal },
          )
          if (cancelled) return
          cacheRef.current.set(normalizedQuery, fullPayload)
          setCorFormSearchResult({ query: normalizedQuery, payload: fullPayload })
          const fullExact = hasExactCorFormMatch(fullPayload.groups ?? [], normalizedQuery)
          setCorDidYouMean(fullExact ? null : (fullPayload.did_you_mean ?? null))
        } catch (error) {
          if (!cancelled && error instanceof Error) {
            toast.error(error.message)
          }
        } finally {
          if (!cancelled) {
            setIsCorLookupLoading(false)
            setIsCorTranslationsLoading(false)
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
      setIsCorLookupLoading(false)
      setIsCorTranslationsLoading(false)
    }
  }, [apiClient, normalizedQuery, resetVersion, shouldSkipLookup])

  return { corDidYouMean, corFormSearchResult, isCorLookupLoading, isCorTranslationsLoading }
}
