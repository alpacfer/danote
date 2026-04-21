import { useEffect, useRef, useState } from "react"

import {
  SEARCH_RESOLVE_DEBOUNCE_MS,
  normalizeSearchWord,
  type WordbankSearchItem,
  type WordbankSearchResponse,
} from "@/app/core"
import type { SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

export function useSidebarWordbankSearch({
  apiClient,
  isSentenceMode,
  normalizedQuery,
  resetVersion,
}: {
  apiClient: SidebarApiClient
  isSentenceMode: boolean
  normalizedQuery: string
  resetVersion: string
}) {
  const cacheRef = useRef<Map<string, { matches: WordbankSearchItem[]; correction: string | null }>>(new Map())
  const [searchApiMatches, setSearchApiMatches] = useState<WordbankSearchItem[]>([])
  const [wordbankDidYouMean, setWordbankDidYouMean] = useState<string | null>(null)

  useEffect(() => {
    cacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setSearchApiMatches([])
      setWordbankDidYouMean(null)
    }, 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    let cancelled = false
    const commitSearchMatches = (nextMatches: WordbankSearchItem[]) => {
      window.setTimeout(() => {
        if (!cancelled) {
          setSearchApiMatches(nextMatches)
        }
      }, 0)
    }
    const commitDidYouMean = (nextCorrection: string | null) => {
      window.setTimeout(() => {
        if (!cancelled) {
          setWordbankDidYouMean(nextCorrection)
        }
      }, 0)
    }

    if (isSentenceMode || !normalizedQuery || normalizedQuery.length < 2) {
      commitSearchMatches([])
      commitDidYouMean(null)
      return () => {
        cancelled = true
      }
    }

    const cached = cacheRef.current.get(normalizedQuery)
    if (cached) {
      commitDidYouMean(cached.correction)
      commitSearchMatches(cached.matches)
      return () => {
        cancelled = true
      }
    }

    commitSearchMatches([])

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const payload = await apiClient.tryGetJson<WordbankSearchResponse>(
            `/api/wordbank/search?query=${encodeURIComponent(normalizedQuery)}&limit=8`,
            { signal: controller.signal },
          )
          if (!payload) {
            if (!cancelled) {
              commitSearchMatches([])
            }
            return
          }
          if (cancelled) {
            return
          }
          const correction = payload.did_you_mean ?? null
          const effectiveQuery = correction ?? normalizedQuery
          const exactMatches = (payload.items ?? []).filter((item) => {
            const lemmaKey = normalizeSearchWord(item.lemma)
            const matchSurfaceKey = normalizeSearchWord(item.match_surface ?? "")
            return lemmaKey === effectiveQuery || matchSurfaceKey === effectiveQuery
          })
          cacheRef.current.set(normalizedQuery, { matches: exactMatches, correction })
          commitDidYouMean(correction)
          commitSearchMatches(exactMatches)
        } catch {
          if (!cancelled) {
            commitDidYouMean(null)
            commitSearchMatches([])
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [apiClient, isSentenceMode, normalizedQuery, resetVersion])

  return { searchApiMatches, wordbankDidYouMean }
}
