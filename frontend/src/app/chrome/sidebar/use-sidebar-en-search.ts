import { useEffect, useMemo, useRef, useState } from "react"

import {
  SEARCH_RESOLVE_DEBOUNCE_MS,
  isShortLetterWord,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type ENSearchFormResponse,
} from "@/app/core"
import { buildEnTranslatedCorResults } from "@/app/chrome/sidebar/sidebar-search-query"
import type { EnResolveResult, SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

export function useSidebarEnSearch({
  apiClient,
  isEnglishSingleWordQuery,
  isSentenceMode,
  normalizedQuery,
  resetVersion,
}: {
  apiClient: SidebarApiClient
  isEnglishSingleWordQuery: boolean
  isSentenceMode: boolean
  normalizedQuery: string
  resetVersion: string
}) {
  const enResolveCacheRef = useRef<Map<string, EnResolveResult>>(new Map())
  const enTranslatedCorCacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const [enResolveResult, setEnResolveResult] = useState<EnResolveResult | null>(null)
  const [isEnResolveLoading, setIsEnResolveLoading] = useState(false)
  const [enTranslatedCorPayloads, setEnTranslatedCorPayloads] = useState<{
    query: string
    payloads: Record<string, CORSearchFormResponse>
  } | null>(null)
  const [isEnTranslatedCorLoading, setIsEnTranslatedCorLoading] = useState(false)

  useEffect(() => {
    enResolveCacheRef.current.clear()
    enTranslatedCorCacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setEnResolveResult(null)
      setEnTranslatedCorPayloads(null)
      setIsEnResolveLoading(false)
      setIsEnTranslatedCorLoading(false)
    }, 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    if (
      isSentenceMode
      || !normalizedQuery
      || normalizedQuery.length < 2
      || /\s/u.test(normalizedQuery)
      || isShortLetterWord(normalizedQuery)
      || !isEnglishSingleWordQuery
    ) {
      setEnResolveResult(null)
      setIsEnResolveLoading(false)
      return
    }

    const cached = enResolveCacheRef.current.get(normalizedQuery)
    if (cached) {
      setEnResolveResult(cached)
      setIsEnResolveLoading(false)
      return
    }

    let cancelled = false
    setIsEnResolveLoading(true)
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const payload = await apiClient
            .getJson<ENSearchFormResponse>(
              `/api/wordbank/search/en-form?form=${encodeURIComponent(normalizedQuery)}`,
              "English search is unavailable.",
            )
            .catch(() => null)
          if (cancelled || !payload) return
          const nextResult: EnResolveResult = {
            query: normalizedQuery,
            groups: payload.groups ?? [],
          }
          enResolveCacheRef.current.set(normalizedQuery, nextResult)
          setEnResolveResult(nextResult)
        } finally {
          if (!cancelled) setIsEnResolveLoading(false)
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      setIsEnResolveLoading(false)
    }
  }, [apiClient, isEnglishSingleWordQuery, isSentenceMode, normalizedQuery, resetVersion])

  const activeEnResolveResult = useMemo(() => {
    if (!enResolveResult || enResolveResult.query !== normalizedQuery) return null
    return enResolveResult
  }, [enResolveResult, normalizedQuery])

  useEffect(() => {
    if (!activeEnResolveResult || activeEnResolveResult.groups.length === 0) {
      setEnTranslatedCorPayloads(null)
      setIsEnTranslatedCorLoading(false)
      return
    }

    const translationKeys = Array.from(
      new Set(
        activeEnResolveResult.groups
          .map((group) => normalizeSearchWord(group.danish_translation ?? ""))
          .filter(Boolean),
      ),
    )
    if (translationKeys.length === 0) {
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: {} })
      setIsEnTranslatedCorLoading(false)
      return
    }

    const cachedPayloads: Record<string, CORSearchFormResponse> = {}
    const missing = translationKeys.filter((translationKey) => {
      const cached = enTranslatedCorCacheRef.current.get(translationKey)
      if (cached) {
        cachedPayloads[translationKey] = cached
        return false
      }
      return true
    })

    if (missing.length === 0) {
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: cachedPayloads })
      setIsEnTranslatedCorLoading(false)
      return
    }

    let cancelled = false
    setIsEnTranslatedCorLoading(true)
    void Promise.all(
      missing.map(async (translationKey) => {
        const payload = await apiClient
          .getJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(translationKey)}&limit=100`,
            "Search translation is unavailable.",
          )
          .catch(() => null)
        if (!payload) {
          return null
        }
        return { translationKey, payload }
      }),
    ).then((results) => {
      if (cancelled) {
        return
      }
      const mergedPayloads = { ...cachedPayloads }
      for (const item of results) {
        if (!item) {
          continue
        }
        enTranslatedCorCacheRef.current.set(item.translationKey, item.payload)
        mergedPayloads[item.translationKey] = item.payload
      }
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: mergedPayloads })
      setIsEnTranslatedCorLoading(false)
    })

    return () => {
      cancelled = true
      setIsEnTranslatedCorLoading(false)
    }
  }, [activeEnResolveResult, apiClient, normalizedQuery])

  const activeEnTranslatedCorResults = useMemo(() => {
    const payloads = enTranslatedCorPayloads?.query === normalizedQuery
      ? enTranslatedCorPayloads.payloads
      : {}
    return buildEnTranslatedCorResults(activeEnResolveResult, payloads, normalizedQuery)
  }, [activeEnResolveResult, enTranslatedCorPayloads, normalizedQuery])

  return {
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
  }
}
