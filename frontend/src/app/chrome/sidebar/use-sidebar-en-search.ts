import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  ApiRequestError,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  isBlockedShortSearchWord,
  normalizeSearchWord,
  type CORSearchFormBatchResponse,
  type CORSearchFormResponse,
  type ENSearchFormResponse,
} from "@/app/core"
import { buildEnTranslatedCorResults } from "@/app/chrome/sidebar/sidebar-search-query"
import { searchAttemptKey } from "@/app/chrome/sidebar/sidebar-search-types"
import type { EnResolveResult, SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"
import { isEnglishPronounQuery } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { isEnglishQuestionWordQuery } from "@/app/sections/wordbank/question-words/question-words-data"

export function useSidebarEnSearch({
  apiClient,
  isEnglishSingleWordQuery,
  isSentenceMode,
  normalizedQuery,
  resetVersion,
  onTrialLimitReached,
}: {
  apiClient: SidebarApiClient
  isEnglishSingleWordQuery: boolean
  isSentenceMode: boolean
  normalizedQuery: string
  resetVersion: string
  onTrialLimitReached: (key: string) => void
}) {
  const reportSearchError = useCallback(
    (error: unknown): null => {
      if (error instanceof ApiRequestError && error.status === 429) {
        onTrialLimitReached(searchAttemptKey(resetVersion, normalizedQuery))
      }
      return null
    },
    [normalizedQuery, onTrialLimitReached, resetVersion],
  )
  const enResolveCacheRef = useRef<Map<string, EnResolveResult>>(new Map())
  const enTranslatedCorCacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const [enResolveResult, setEnResolveResult] = useState<EnResolveResult | null>(null)
  const [isEnResolveLoading, setIsEnResolveLoading] = useState(false)
  const [enTranslatedCorPayloads, setEnTranslatedCorPayloads] = useState<{
    query: string
    payloads: Record<string, CORSearchFormResponse>
  } | null>(null)
  const [isEnTranslatedCorLoading, setIsEnTranslatedCorLoading] = useState(false)
  const [enTranslatedCorSkeletonCount, setEnTranslatedCorSkeletonCount] = useState(0)

  useEffect(() => {
    enResolveCacheRef.current.clear()
    enTranslatedCorCacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setEnResolveResult(null)
      setEnTranslatedCorPayloads(null)
      setIsEnResolveLoading(false)
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
    }, 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    if (
      isSentenceMode
      || !normalizedQuery
      || normalizedQuery.length < 2
      || /\s/u.test(normalizedQuery)
      || isBlockedShortSearchWord(normalizedQuery)
      || isEnglishQuestionWordQuery(normalizedQuery)
      || isEnglishPronounQuery(normalizedQuery)
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
            .catch(reportSearchError)
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
  }, [apiClient, isEnglishSingleWordQuery, isSentenceMode, normalizedQuery, reportSearchError, resetVersion])

  const activeEnResolveResult = useMemo(() => {
    if (!enResolveResult || enResolveResult.query !== normalizedQuery) return null
    return enResolveResult
  }, [enResolveResult, normalizedQuery])

  useEffect(() => {
    if (!activeEnResolveResult || activeEnResolveResult.groups.length === 0) {
      setEnTranslatedCorPayloads(null)
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
      return
    }

    const posByTranslationKey = new Map<string, Set<string>>()
    for (const group of activeEnResolveResult.groups) {
      const key = normalizeSearchWord(group.danish_translation ?? "")
      if (!key) continue
      const posSet = posByTranslationKey.get(key) ?? new Set<string>()
      const pos = (group.pos_ud ?? "").toString().trim().toUpperCase()
      if (pos) posSet.add(pos)
      posByTranslationKey.set(key, posSet)
    }
    const translationKeys = Array.from(posByTranslationKey.keys())
    const enPosForKey = (translationKey: string): string => {
      const posSet = posByTranslationKey.get(translationKey)
      return posSet ? Array.from(posSet).sort().join(",") : ""
    }
    if (translationKeys.length === 0) {
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: {} })
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
      return
    }

    const filteredCacheKey = (translationKey: string) =>
      `${normalizedQuery}::${enPosForKey(translationKey)}::${translationKey}`
    const cachedPayloads: Record<string, CORSearchFormResponse> = {}
    const missing = translationKeys.filter((translationKey) => {
      const cached = enTranslatedCorCacheRef.current.get(filteredCacheKey(translationKey))
      if (cached) {
        cachedPayloads[translationKey] = cached
        return false
      }
      return true
    })

    if (missing.length === 0) {
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: cachedPayloads })
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
      return
    }

    let cancelled = false
    setIsEnTranslatedCorLoading(true)
    setEnTranslatedCorSkeletonCount(0)
    void (async () => {
      const partialResults = await Promise.all(
        missing.map(async (translationKey) => {
          const payload = await apiClient
            .getJson<CORSearchFormResponse>(
              `/api/wordbank/search/cor-form?form=${encodeURIComponent(translationKey)}&limit=100&include_translations=false`,
              "Search translation is unavailable.",
            )
            .catch(reportSearchError)
          return payload ? { translationKey, payload } : null
        }),
      )
      if (cancelled) {
        return
      }
      if (partialResults.every(Boolean)) {
        const partialPayloads = { ...cachedPayloads }
        for (const item of partialResults) {
          if (item) {
            partialPayloads[item.translationKey] = item.payload
          }
        }
        const pendingResults = buildEnTranslatedCorResults(activeEnResolveResult, partialPayloads, normalizedQuery)
        setEnTranslatedCorSkeletonCount(
          pendingResults.corSearchVariantsToRender.length + pendingResults.fallbackEnPosGroups.length,
        )
      }

      const batchPayload = await apiClient
        .postJson<CORSearchFormBatchResponse>(
          "/api/wordbank/search/cor-form-batch",
          {
            limit: 100,
            include_translations: true,
            items: missing.map((translationKey) => ({
              form: translationKey,
              en_query: normalizedQuery,
              en_pos_ud: enPosForKey(translationKey) || null,
            })),
          },
          "Search translation is unavailable.",
        )
        .catch(reportSearchError)
      if (cancelled) {
        return
      }
      const mergedPayloads = { ...cachedPayloads }
      if (batchPayload) {
        batchPayload.items.forEach((payload, index) => {
          const translationKey = missing[index]
          if (!translationKey) return
          enTranslatedCorCacheRef.current.set(filteredCacheKey(translationKey), payload)
          mergedPayloads[translationKey] = payload
        })
      }
      setEnTranslatedCorPayloads({ query: normalizedQuery, payloads: mergedPayloads })
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
    })()

    return () => {
      cancelled = true
      setIsEnTranslatedCorLoading(false)
      setEnTranslatedCorSkeletonCount(0)
    }
  }, [activeEnResolveResult, apiClient, normalizedQuery, reportSearchError])

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
    enTranslatedCorSkeletonCount,
  }
}
