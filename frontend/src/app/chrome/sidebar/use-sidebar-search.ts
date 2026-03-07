import { useEffect, useMemo, useRef, useState } from "react"

import {
  BACKEND_URL,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  createApiClient,
  isShortLetterWord,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type SavedNote,
  type WordbankLemma,
  type WordbankSearchResponse,
} from "@/app/core"

type UseSidebarSearchParams = {
  savedNotes: SavedNote[]
  wordbankCacheVersion: number
}

type SearchMatch = { lemma: WordbankLemma; matchSurface: string | null }
export function useSidebarSearch({
  savedNotes,
  wordbankCacheVersion,
}: UseSidebarSearchParams) {
  const [searchQuery, setSearchQuery] = useState("")
  const corFormSearchCacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const wordbankSearchCacheRef = useRef<Map<string, SearchMatch[]>>(new Map())
  const [searchApiMatches, setSearchApiMatches] = useState<SearchMatch[]>([])
  const [corFormSearchResult, setCorFormSearchResult] = useState<{ query: string; payload: CORSearchFormResponse } | null>(null)
  const apiClient = useMemo(() => createApiClient({ backendUrl: BACKEND_URL }), [])

  const normalizedQuery = normalizeSearchWord(searchQuery)
  const trimmedQuery = normalizedQuery

  const matchingNotes = useMemo(() => {
    if (!normalizedQuery) {
      return []
    }
    return savedNotes
      .filter((note) => {
        const name = note.name.trim().toLocaleLowerCase("da-DK")
        const text = note.text.trim().toLocaleLowerCase("da-DK")
        return name.includes(normalizedQuery) || text.includes(normalizedQuery)
      })
      .slice(0, 8)
  }, [normalizedQuery, savedNotes])

  useEffect(() => {
    wordbankSearchCacheRef.current.clear()
    corFormSearchCacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setSearchApiMatches([])
      setCorFormSearchResult(null)
    }, 0)
    return () => {
      window.clearTimeout(clearId)
    }
  }, [wordbankCacheVersion])

  useEffect(() => {
    let cancelled = false
    const commitSearchMatches = (nextMatches: SearchMatch[]) => {
      window.setTimeout(() => {
        if (!cancelled) {
          setSearchApiMatches(nextMatches)
        }
      }, 0)
    }

    if (!normalizedQuery) {
      commitSearchMatches([])
      return () => {
        cancelled = true
      }
    }

    const cached = wordbankSearchCacheRef.current.get(normalizedQuery)
    if (cached) {
      commitSearchMatches(cached)
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
            `/api/wordbank/search?query=${encodeURIComponent(trimmedQuery)}&limit=8`,
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
          const mapped = (payload.items ?? []).map((item) => ({
            lemma: {
              lemma: item.lemma,
              display_lemma: item.display_lemma,
              english_translation: item.english_translation,
              variation_count: item.variation_count,
              pos_tag: item.pos_tag ?? null,
              morphology: item.morphology ?? null,
            },
            matchSurface: item.match_surface ?? null,
          }))
          wordbankSearchCacheRef.current.set(normalizedQuery, mapped)
          commitSearchMatches(mapped)
        } catch {
          if (!cancelled) {
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
  }, [apiClient, normalizedQuery, trimmedQuery, wordbankCacheVersion])

  useEffect(() => {
    if (!normalizedQuery || /\s/u.test(normalizedQuery) || isShortLetterWord(normalizedQuery)) {
      return
    }

    const cachedPayload = corFormSearchCacheRef.current.get(normalizedQuery)
    if (cachedPayload) {
      setCorFormSearchResult({
        query: normalizedQuery,
        payload: cachedPayload,
      })
      return
    }

    const controller = new AbortController()
    let cancelled = false
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const payload = await apiClient.tryGetJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(trimmedQuery)}&limit=100`,
            { signal: controller.signal },
          )
          if (!payload) {
            setCorFormSearchResult((current) => (current?.query === normalizedQuery ? null : current))
            return
          }
          if (cancelled) {
            return
          }
          corFormSearchCacheRef.current.set(normalizedQuery, payload)
          setCorFormSearchResult({
            query: normalizedQuery,
            payload,
          })
        } catch {
          if (!cancelled) {
            setCorFormSearchResult((current) => (current?.query === normalizedQuery ? null : current))
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [apiClient, normalizedQuery, trimmedQuery, wordbankCacheVersion])

  const activeCorFormSearchResult = useMemo(() => {
    if (!corFormSearchResult || corFormSearchResult.query !== normalizedQuery) {
      return null
    }
    return corFormSearchResult
  }, [corFormSearchResult, normalizedQuery])

  return {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    activeCorFormSearchResult,
  }
}
