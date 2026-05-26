import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import {
  ApiRequestError,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  isBlockedShortSearchWord,
  type CORSearchFormResponse,
  type ENPosGroup,
} from "@/app/core"
import { getPronounCategory } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { getQuestionWordEntry } from "@/app/sections/wordbank/question-words/question-words-data"
import { hasExactCorFormMatch } from "@/app/chrome/sidebar/sidebar-search-query"
import { searchAttemptKey } from "@/app/chrome/sidebar/sidebar-search-types"
import type { CorFormSearchResult, SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

export function useSidebarCorSearch({
  apiClient,
  shouldSkipLookup,
  normalizedQuery,
  resetVersion,
  searchAttemptVersion,
  onTrialLimitReached,
  enResolveGroups,
}: {
  apiClient: SidebarApiClient
  shouldSkipLookup: boolean
  normalizedQuery: string
  resetVersion: string
  searchAttemptVersion: string
  onTrialLimitReached: (key: string) => void
  enResolveGroups?: ENPosGroup[]
}) {
  const cacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const partialCacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const [corDidYouMean, setCorDidYouMean] = useState<string | null>(null)
  const [corFormSearchResult, setCorFormSearchResult] = useState<CorFormSearchResult | null>(null)
  const [isCorLookupLoading, setIsCorLookupLoading] = useState(false)
  const [isCorTranslationsLoading, setIsCorTranslationsLoading] = useState(false)

  useEffect(() => {
    cacheRef.current.clear()
    partialCacheRef.current.clear()
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
      || isBlockedShortSearchWord(normalizedQuery)
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
    const cachedPartialPayload = partialCacheRef.current.get(normalizedQuery)

    const controller = new AbortController()
    let cancelled = false
    setIsCorLookupLoading(true)
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const partialPayload = cachedPartialPayload
            ?? await apiClient.tryGetJson<CORSearchFormResponse>(
              `/api/wordbank/search/cor-form?form=${encodeURIComponent(normalizedQuery)}&limit=100&include_translations=false`,
              { signal: controller.signal },
            )
          if (cancelled) return
          if (partialPayload) {
            partialCacheRef.current.set(normalizedQuery, partialPayload)
            setCorFormSearchResult({ query: normalizedQuery, payload: partialPayload })
            const partialExact = hasExactCorFormMatch(partialPayload.groups ?? [], normalizedQuery)
            setCorDidYouMean(partialExact ? null : (partialPayload.did_you_mean ?? null))
            if (shouldSkipDirectCorFull(partialPayload, normalizedQuery, enResolveGroups ?? [])) {
              setIsCorTranslationsLoading(false)
              return
            }
            setIsCorTranslationsLoading(true)
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
          if (!cancelled) {
            if (error instanceof ApiRequestError && error.status === 429) {
              onTrialLimitReached(searchAttemptKey(searchAttemptVersion, normalizedQuery))
            } else if (error instanceof Error) {
              toast.error(error.message)
            }
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
  }, [
    apiClient,
    enResolveGroups,
    normalizedQuery,
    onTrialLimitReached,
    resetVersion,
    searchAttemptVersion,
    shouldSkipLookup,
  ])

  return { corDidYouMean, corFormSearchResult, isCorLookupLoading, isCorTranslationsLoading }
}

function shouldSkipDirectCorFull(
  partialPayload: CORSearchFormResponse,
  normalizedQuery: string,
  enResolveGroups: ENPosGroup[],
): boolean {
  if (enResolveGroups.length === 0) return false
  const groups = partialPayload.groups ?? []
  if (groups.length === 0) return true
  return groups.every((group) => {
    if ((group.gloss ?? "").trim()) return false
    const pos = (group.pos_tag ?? "").trim().toUpperCase()
    if (pos !== "VERB") return false
    return (group.variants ?? []).every((variant) => {
      const form = (variant.form ?? "").trim().toLowerCase()
      const lemma = (variant.lemma ?? "").trim().toLowerCase()
      const gloss = (variant.gloss ?? "").trim()
      return form === normalizedQuery && lemma !== normalizedQuery && !gloss
    })
  })
}
