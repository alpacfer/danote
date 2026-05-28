import { useEffect, useRef, useState } from "react"

import {
  SEARCH_RESOLVE_DEBOUNCE_MS,
  isBlockedShortSearchWord,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type ENSearchFormResponse,
  type SentenceSearchPreviewResponse,
  type WordbankSearchItem,
  type WordbankSearchResponse,
} from "@/app/core"
import { hasDanishSentenceHint, hasExactCorFormMatch } from "@/app/chrome/sidebar/sidebar-search-query"
import type { SearchLanguageMode, SearchModeSwitchSuggestion, SidebarApiClient } from "@/app/chrome/sidebar/sidebar-search-types"

type CachedSuggestion = SearchModeSwitchSuggestion | null

function credibleSavedMatches(items: WordbankSearchItem[], normalizedQuery: string): WordbankSearchItem[] {
  return items.filter((item) => {
    if (item.matched_via) return true
    return normalizeSearchWord(item.lemma) === normalizedQuery
      || normalizeSearchWord(item.match_surface ?? "") === normalizedQuery
  })
}

function suggestionFor(targetMode: SearchLanguageMode, reason: string): SearchModeSwitchSuggestion {
  return {
    targetMode,
    value: targetMode === "en" ? "switch-search-mode-en" : "switch-search-mode-da",
    label: targetMode === "en" ? "Search in English instead?" : "Search in Danish instead?",
    evidenceLabel: reason,
  }
}

export function useSidebarModeSuggestion({
  apiClient,
  searchLanguageMode,
  normalizedQuery,
  sentenceQuery,
  isSentenceMode,
  isNumberMode,
  resetVersion,
}: {
  apiClient: SidebarApiClient
  searchLanguageMode: SearchLanguageMode
  normalizedQuery: string
  sentenceQuery: string
  isSentenceMode: boolean
  isNumberMode: boolean
  resetVersion: string
}) {
  const cacheRef = useRef<Map<string, CachedSuggestion>>(new Map())
  const [modeSwitchSuggestion, setModeSwitchSuggestion] = useState<SearchModeSwitchSuggestion | null>(null)

  useEffect(() => {
    cacheRef.current.clear()
    const clearId = window.setTimeout(() => setModeSwitchSuggestion(null), 0)
    return () => window.clearTimeout(clearId)
  }, [resetVersion])

  useEffect(() => {
    const targetMode: SearchLanguageMode = searchLanguageMode === "da" ? "en" : "da"
    const query = isSentenceMode ? sentenceQuery : normalizedQuery
    const cacheKey = `${targetMode}:${isSentenceMode ? "sentence" : "word"}:${query}`
    let cancelled = false

    if (
      isNumberMode
      || !query
      || (!isSentenceMode && (normalizedQuery.length < 2 || /\s/u.test(normalizedQuery) || isBlockedShortSearchWord(normalizedQuery)))
    ) {
      const clearId = window.setTimeout(() => {
        if (!cancelled) {
          setModeSwitchSuggestion(null)
        }
      }, 0)
      return () => {
        cancelled = true
        window.clearTimeout(clearId)
      }
    }

    if (cacheRef.current.has(cacheKey)) {
      const commitId = window.setTimeout(() => {
        if (!cancelled) {
          setModeSwitchSuggestion(cacheRef.current.get(cacheKey) ?? null)
        }
      }, 0)
      return () => {
        cancelled = true
        window.clearTimeout(commitId)
      }
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      void (async () => {
        let suggestion: SearchModeSwitchSuggestion | null = null
        try {
          if (isSentenceMode) {
            const payload = await apiClient.postJson<SentenceSearchPreviewResponse>(
              "/api/sentencebank/search-preview",
              { source_text: sentenceQuery, fast: true, language_mode: null },
              "Could not prepare sentence preview.",
              { signal: controller.signal },
            )
            const hasDanishHint = hasDanishSentenceHint(sentenceQuery)
            const effectiveLanguage = payload.query_language === "en" && hasDanishHint ? "da" : payload.query_language
            if (effectiveLanguage === targetMode) {
              suggestion = suggestionFor(targetMode, `${targetMode === "en" ? "English" : "Danish"} sentence detected`)
            }
          } else if (targetMode === "en") {
            const [wordbank, enForm] = await Promise.all([
              apiClient.tryGetJson<WordbankSearchResponse>(
                `/api/wordbank/search?query=${encodeURIComponent(normalizedQuery)}&limit=1&language=en`,
                { signal: controller.signal },
              ),
              apiClient.tryGetJson<ENSearchFormResponse>(
                `/api/wordbank/search/en-form?form=${encodeURIComponent(normalizedQuery)}&include_translations=false`,
                { signal: controller.signal },
              ),
            ])
            const savedCount = credibleSavedMatches(wordbank?.items ?? [], normalizedQuery).length
            const enGroupCount = enForm?.groups?.length ?? 0
            if (savedCount > 0) {
              suggestion = suggestionFor("en", "English saved match found")
            } else if (enGroupCount > 0) {
              suggestion = suggestionFor("en", "English dictionary match found")
            }
          } else {
            const [wordbank, corForm] = await Promise.all([
              apiClient.tryGetJson<WordbankSearchResponse>(
                `/api/wordbank/search?query=${encodeURIComponent(normalizedQuery)}&limit=1&language=da`,
                { signal: controller.signal },
              ),
              apiClient.tryGetJson<CORSearchFormResponse>(
                `/api/wordbank/search/cor-form?form=${encodeURIComponent(normalizedQuery)}&limit=20&include_translations=false`,
                { signal: controller.signal },
              ),
            ])
            const savedCount = credibleSavedMatches(wordbank?.items ?? [], normalizedQuery).length
            const hasExactCor = hasExactCorFormMatch(corForm?.groups ?? [], normalizedQuery)
            if (savedCount > 0) {
              suggestion = suggestionFor("da", "Danish saved match found")
            } else if (hasExactCor) {
              suggestion = suggestionFor("da", "Danish dictionary match found")
            }
          }
        } catch {
          suggestion = null
        }

        if (!cancelled) {
          cacheRef.current.set(cacheKey, suggestion)
          setModeSwitchSuggestion(suggestion)
        }
      })()
    }, SEARCH_RESOLVE_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [apiClient, isNumberMode, isSentenceMode, normalizedQuery, resetVersion, searchLanguageMode, sentenceQuery])

  return { modeSwitchSuggestion }
}
