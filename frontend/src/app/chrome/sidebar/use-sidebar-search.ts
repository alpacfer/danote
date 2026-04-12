import { useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import {
  BACKEND_URL,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  SENTENCE_VERIFY_DEBOUNCE_MS,
  createApiClient,
  hasMultipleWords,
  isShortLetterWord,
  type GeneratePhraseTranslationResponse,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type SavedNote,
  type WordbankSearchItem,
  type WordbankSearchResponse,
  type VerifySentenceResponse,
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
  const wordbankSearchCacheRef = useRef<Map<string, WordbankSearchItem[]>>(new Map())
  const [searchApiMatches, setSearchApiMatches] = useState<WordbankSearchItem[]>([])
  const [wordbankDidYouMean, setWordbankDidYouMean] = useState<string | null>(null)
  const [corDidYouMean, setCorDidYouMean] = useState<string | null>(null)
  const [corFormSearchResult, setCorFormSearchResult] = useState<{ query: string; payload: CORSearchFormResponse } | null>(null)
  const [isCorTranslationsLoading, setIsCorTranslationsLoading] = useState(false)
  const [sentenceSearchResult, setSentenceSearchResult] = useState<{
    query: string
    source_text: string
    english_translation: string | null
  } | null>(null)
  const [isSentenceTranslationLoading, setIsSentenceTranslationLoading] = useState(false)
  const [sentenceVerification, setSentenceVerification] = useState<{ query: string; result: VerifySentenceResponse } | null>(null)
  const [isSentenceVerificationLoading, setIsSentenceVerificationLoading] = useState(false)
  const [sentenceVerificationError, setSentenceVerificationError] = useState<string | null>(null)
  const sentenceVerificationCacheRef = useRef<Map<string, VerifySentenceResponse>>(new Map())
  const apiClient = useMemo(
    () => createApiClient({ backendUrl: BACKEND_URL, extractErrorMessage }),
    [],
  )

  const normalizedQuery = normalizeSearchWord(searchQuery)
  const trimmedQuery = normalizedQuery
  const isSentenceMode = hasMultipleWords(trimmedQuery) && trimmedQuery.length <= 50

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
      setSentenceSearchResult(null)
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
          const correction = payload.did_you_mean ?? null
          const effectiveQuery = correction ?? normalizedQuery
          const exactMatches = (payload.items ?? []).filter((item) => {
            const lemmaKey = normalizeSearchWord(item.lemma)
            const matchSurfaceKey = normalizeSearchWord(item.match_surface ?? "")
            return lemmaKey === effectiveQuery || matchSurfaceKey === effectiveQuery
          })
          wordbankSearchCacheRef.current.set(normalizedQuery, exactMatches)
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
    if (!isSentenceMode || !trimmedQuery) {
      setSentenceSearchResult(null)
      setIsSentenceTranslationLoading(false)
      return
    }

    let cancelled = false
    setSentenceSearchResult({
      query: normalizedQuery,
      source_text: trimmedQuery,
      english_translation: null,
    })
    setIsSentenceTranslationLoading(true)

    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const payload = await apiClient.postJson<GeneratePhraseTranslationResponse>(
            "/api/wordbank/phrase-translation",
            { source_text: trimmedQuery },
            "Could not generate phrase translation.",
          )
          if (cancelled) {
            return
          }
          setSentenceSearchResult({
            query: normalizedQuery,
            source_text: payload.source_text || trimmedQuery,
            english_translation: payload.english_translation ?? null,
          })
        } catch {
          if (!cancelled) {
            setSentenceSearchResult({
              query: normalizedQuery,
              source_text: trimmedQuery,
              english_translation: null,
            })
          }
        } finally {
          if (!cancelled) {
            setIsSentenceTranslationLoading(false)
          }
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      setIsSentenceTranslationLoading(false)
    }
  }, [apiClient, isSentenceMode, normalizedQuery, trimmedQuery])

  useEffect(() => {
    if (!isSentenceMode || !trimmedQuery) {
      setSentenceVerification(null)
      setSentenceVerificationError(null)
      setIsSentenceVerificationLoading(false)
      return
    }

    const cached = sentenceVerificationCacheRef.current.get(trimmedQuery)
    if (cached) {
      setSentenceVerification({ query: trimmedQuery, result: cached })
      setIsSentenceVerificationLoading(false)
      setSentenceVerificationError(null)
      return
    }

    let cancelled = false
    setIsSentenceVerificationLoading(true)
    setSentenceVerificationError(null)

    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const result = await apiClient.postJson<VerifySentenceResponse>(
            "/api/sentencebank/verify-sentence",
            { source_text: trimmedQuery },
            "Could not verify sentence.",
          )
          if (cancelled) return
          sentenceVerificationCacheRef.current.set(trimmedQuery, result)
          setSentenceVerification({ query: trimmedQuery, result })
        } catch (error) {
          if (!cancelled) {
            setSentenceVerificationError(error instanceof Error ? error.message : "Could not verify sentence.")
            setSentenceVerification(null)
          }
        } finally {
          if (!cancelled) {
            setIsSentenceVerificationLoading(false)
          }
        }
      })()
    }, SENTENCE_VERIFY_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      setIsSentenceVerificationLoading(false)
    }
  }, [apiClient, isSentenceMode, trimmedQuery])

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
    sentenceSearchResult,
    isSentenceTranslationLoading,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
    sentenceVerification: sentenceVerification?.result ?? null,
    isSentenceVerificationLoading,
    sentenceVerificationError,
  }
}
