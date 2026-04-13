import { useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import {
  BACKEND_URL,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  SENTENCE_VERIFY_DEBOUNCE_MS,
  SENTENCE_VERIFY_MAX_CHARS,
  createApiClient,
  normalizeSentenceText,
  hasMultipleWords,
  isShortLetterWord,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type SavedNote,
  type SentenceSearchPreviewResponse,
  type WordbankSearchItem,
  type WordbankSearchResponse,
} from "@/app/core"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

type UseSidebarSearchParams = {
  savedNotes: SavedNote[]
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
}

export function useSidebarSearch({
  savedNotes,
  wordbankCacheVersion,
  searchTranslationConfigVersion,
}: UseSidebarSearchParams) {
  const [searchQuery, setSearchQuery] = useState("")
  const corFormSearchCacheRef = useRef<Map<string, CORSearchFormResponse>>(new Map())
  const wordbankSearchCacheRef = useRef<Map<string, { matches: WordbankSearchItem[]; correction: string | null }>>(new Map())
  const [searchApiMatches, setSearchApiMatches] = useState<WordbankSearchItem[]>([])
  const [wordbankDidYouMean, setWordbankDidYouMean] = useState<string | null>(null)
  const [corDidYouMean, setCorDidYouMean] = useState<string | null>(null)
  const [corFormSearchResult, setCorFormSearchResult] = useState<{ query: string; payload: CORSearchFormResponse } | null>(null)
  const [isCorTranslationsLoading, setIsCorTranslationsLoading] = useState(false)
  const [sentenceSearchPreview, setSentenceSearchPreview] = useState<{
    query: string
    result: SentenceSearchPreviewResponse
  } | null>(null)
  const [isSentenceSearchPreviewLoading, setIsSentenceSearchPreviewLoading] = useState(false)
  const [sentenceSearchPreviewError, setSentenceSearchPreviewError] = useState<string | null>(null)
  const sentenceSearchPreviewCacheRef = useRef<Map<string, SentenceSearchPreviewResponse>>(new Map())
  const apiClient = useMemo(
    () => createApiClient({ backendUrl: BACKEND_URL, extractErrorMessage }),
    [],
  )

  const sentenceQuery = normalizeSentenceText(searchQuery)
  const normalizedQuery = normalizeSearchWord(searchQuery)
  const trimmedQuery = normalizedQuery
  const isSentenceMode = hasMultipleWords(sentenceQuery) && sentenceQuery.length <= SENTENCE_VERIFY_MAX_CHARS
  const activeSentenceSearchPreview = sentenceSearchPreview?.query === sentenceQuery
    ? sentenceSearchPreview.result
    : null

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
    sentenceSearchPreviewCacheRef.current.clear()
    const clearId = window.setTimeout(() => {
      setSearchApiMatches([])
      setCorFormSearchResult(null)
      setSentenceSearchPreview(null)
      setSentenceSearchPreviewError(null)
    }, 0)
    return () => {
      window.clearTimeout(clearId)
    }
  }, [searchTranslationConfigVersion, wordbankCacheVersion])

  useEffect(() => {
    let cancelled = false
    const commitSearchMatches = (nextMatches: WordbankSearchItem[]) => {
      window.setTimeout(() => {
        if (!cancelled) {
          setSearchApiMatches(nextMatches)
        }
      }, 0)
    }

    if (isSentenceMode || !normalizedQuery || normalizedQuery.length < 2) {
      commitSearchMatches([])
      setWordbankDidYouMean(null)
      return () => {
        cancelled = true
      }
    }

    const cached = wordbankSearchCacheRef.current.get(normalizedQuery)
    if (cached) {
      setWordbankDidYouMean(cached.correction)
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
          const correction = payload.did_you_mean ?? null
          const effectiveQuery = correction ?? normalizedQuery
          const exactMatches = (payload.items ?? []).filter((item) => {
            const lemmaKey = normalizeSearchWord(item.lemma)
            const matchSurfaceKey = normalizeSearchWord(item.match_surface ?? "")
            return lemmaKey === effectiveQuery || matchSurfaceKey === effectiveQuery
          })
          wordbankSearchCacheRef.current.set(normalizedQuery, { matches: exactMatches, correction })
          setWordbankDidYouMean(correction)
          commitSearchMatches(exactMatches)
        } catch {
          if (!cancelled) {
            setWordbankDidYouMean(null)
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
  }, [apiClient, isSentenceMode, normalizedQuery, searchTranslationConfigVersion, trimmedQuery, wordbankCacheVersion])

  useEffect(() => {
    if (isSentenceMode || !normalizedQuery || /\s/u.test(normalizedQuery) || isShortLetterWord(normalizedQuery)) {
      setIsCorTranslationsLoading(false)
      setCorDidYouMean(null)
      return
    }

    const cachedPayload = corFormSearchCacheRef.current.get(normalizedQuery)
    if (cachedPayload) {
      setCorFormSearchResult({ query: normalizedQuery, payload: cachedPayload })
      setCorDidYouMean(cachedPayload.did_you_mean ?? null)
      setIsCorTranslationsLoading(false)
      return
    }

    const controller = new AbortController()
    let cancelled = false
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          // Phase 1: fetch words immediately without translations
          const partialPayload = await apiClient.tryGetJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(trimmedQuery)}&limit=100&include_translations=false`,
            { signal: controller.signal },
          )
          if (cancelled) return
          if (partialPayload) {
            setCorFormSearchResult({ query: normalizedQuery, payload: partialPayload })
            setIsCorTranslationsLoading(true)
            setCorDidYouMean(partialPayload.did_you_mean ?? null)
          }

          // Phase 2: fetch again with translations to fill in
          const fullPayload = await apiClient.getJson<CORSearchFormResponse>(
            `/api/wordbank/search/cor-form?form=${encodeURIComponent(trimmedQuery)}&limit=100`,
            "Search translation is unavailable.",
            { signal: controller.signal },
          )
          if (cancelled) return
          corFormSearchCacheRef.current.set(normalizedQuery, fullPayload)
          setCorFormSearchResult({ query: normalizedQuery, payload: fullPayload })
          setCorDidYouMean(fullPayload.did_you_mean ?? null)
        } catch (error) {
          if (!cancelled && error instanceof Error) {
            toast.error(error.message)
          }
        } finally {
          if (!cancelled) {
            setIsCorTranslationsLoading(false)
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
      setIsCorTranslationsLoading(false)
    }
  }, [apiClient, isSentenceMode, normalizedQuery, searchTranslationConfigVersion, trimmedQuery, wordbankCacheVersion])

  useEffect(() => {
    if (!isSentenceMode || !sentenceQuery) {
      setSentenceSearchPreview(null)
      setSentenceSearchPreviewError(null)
      setIsSentenceSearchPreviewLoading(false)
      return
    }

    const cached = sentenceSearchPreviewCacheRef.current.get(sentenceQuery)
    if (cached) {
      setSentenceSearchPreview({ query: sentenceQuery, result: cached })
      setIsSentenceSearchPreviewLoading(false)
      setSentenceSearchPreviewError(null)
      return
    }

    let cancelled = false
    setSentenceSearchPreview(null)
    setIsSentenceSearchPreviewLoading(true)
    setSentenceSearchPreviewError(null)

    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const result = await apiClient.postJson<SentenceSearchPreviewResponse>(
            "/api/sentencebank/search-preview",
            { source_text: sentenceQuery },
            "Could not prepare sentence preview.",
          )
          if (cancelled) return
          sentenceSearchPreviewCacheRef.current.set(sentenceQuery, result)
          setSentenceSearchPreview({ query: sentenceQuery, result })
        } catch (error) {
          if (!cancelled) {
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
          }
        } finally {
          if (!cancelled) {
            setIsSentenceSearchPreviewLoading(false)
          }
        }
      })()
    }, SENTENCE_VERIFY_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      setIsSentenceSearchPreviewLoading(false)
    }
  }, [apiClient, isSentenceMode, sentenceQuery, wordbankCacheVersion, searchTranslationConfigVersion])

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
    isSentenceMode,
    sentenceSearchPreview: activeSentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
    sentenceSearchPreviewError,
  }
}
