import { useCallback, useEffect, useMemo, useState } from "react"

import {
  BACKEND_URL,
  SENTENCE_VERIFY_MAX_CHARS,
  createApiClient,
  normalizeSentenceText,
  hasMultipleWords,
  isBlockedShortSearchWord,
  normalizeSearchWord,
  isAtVerbCandidate,
} from "@/app/core"
import { searchAttemptKey } from "@/app/chrome/sidebar/sidebar-search-types"
import type { SearchLanguageMode, UseSidebarSearchParams } from "@/app/chrome/sidebar/sidebar-search-types"
import { useSidebarCorSearch } from "@/app/chrome/sidebar/use-sidebar-cor-search"
import { useSidebarEnSearch } from "@/app/chrome/sidebar/use-sidebar-en-search"
import { useSidebarModeSuggestion } from "@/app/chrome/sidebar/use-sidebar-mode-suggestion"
import { useSidebarSentencePreview } from "@/app/chrome/sidebar/use-sidebar-sentence-preview"
import { useSidebarWordbankSearch } from "@/app/chrome/sidebar/use-sidebar-wordbank-search"
import { numberFromSearchQuery } from "@/app/sections/wordbank/numbers/numbers-data"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

const SEARCH_LANGUAGE_MODE_STORAGE_KEY = "danote.search.languageMode"

function initialSearchLanguageMode(): SearchLanguageMode {
  if (typeof window === "undefined") return "da"
  try {
    const stored = window.sessionStorage.getItem(SEARCH_LANGUAGE_MODE_STORAGE_KEY)
    return stored === "da" || stored === "en" ? stored : "da"
  } catch {
    return "da"
  }
}

export function useSidebarSearch({
  wordbankCacheVersion,
  searchTranslationConfigVersion,
}: UseSidebarSearchParams) {
  const [searchQuery, setSearchQuery] = useState("")
  const [searchLanguageMode, setSearchLanguageMode] = useState<SearchLanguageMode>(initialSearchLanguageMode)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl: BACKEND_URL, extractErrorMessage }),
    [],
  )
  const resetVersion = `${searchTranslationConfigVersion}:${wordbankCacheVersion}`
  const searchAttemptVersion = `${resetVersion}:${searchLanguageMode}`

  useEffect(() => {
    try {
      window.sessionStorage.setItem(SEARCH_LANGUAGE_MODE_STORAGE_KEY, searchLanguageMode)
    } catch {
      // sessionStorage is best-effort; Danish remains the fallback.
    }
  }, [searchLanguageMode])

  const sentenceQuery = normalizeSentenceText(searchQuery)
  const normalizedQuery = normalizeSearchWord(searchQuery)
  const isNumberMode = numberFromSearchQuery(normalizedQuery) !== null
  const isSentenceMode = !isNumberMode && hasMultipleWords(sentenceQuery) && sentenceQuery.length <= SENTENCE_VERIFY_MAX_CHARS
  const shouldSkipWordLookups = isSentenceMode || isNumberMode
  const isEnglishSingleWordQuery = !isSentenceMode
    && !isNumberMode
    && normalizedQuery.length >= 2
    && !(/\s/u.test(normalizedQuery) && !isAtVerbCandidate(normalizedQuery))
    && !isBlockedShortSearchWord(normalizedQuery)

  // Banner is keyed to the search attempt that hit the cap, so it clears
  // automatically when the user edits the query (no reset effect needed).
  const [trialLimitedKey, setTrialLimitedKey] = useState<string | null>(null)
  const onTrialLimitReached = useCallback(
    (key: string) => setTrialLimitedKey(key),
    [],
  )
  const isTrialLimitReached = trialLimitedKey === searchAttemptKey(searchAttemptVersion, normalizedQuery)

  const { searchApiMatches, wordbankDidYouMean, isWordbankSearchLoading } = useSidebarWordbankSearch({
    apiClient,
    shouldSkipLookup: shouldSkipWordLookups,
    normalizedQuery,
    searchLanguageMode,
    resetVersion,
  })
  const {
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    sentenceSearchPreviewError,
  } = useSidebarSentencePreview({
    apiClient,
    isSentenceMode,
    sentenceQuery,
    searchLanguageMode,
    resetVersion,
  })
  const isMweMode = isSentenceMode && sentenceSearchPreview?.is_multi_word_expression === true
  const {
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  } = useSidebarEnSearch({
    apiClient,
    isEnglishSingleWordQuery: searchLanguageMode === "en" && isEnglishSingleWordQuery,
    isSentenceMode,
    normalizedQuery,
    resetVersion,
    searchAttemptVersion,
    onTrialLimitReached,
  })
  const { corDidYouMean, corFormSearchResult, isCorLookupLoading, isCorTranslationsLoading } = useSidebarCorSearch({
    apiClient,
    shouldSkipLookup: shouldSkipWordLookups || searchLanguageMode === "en",
    normalizedQuery,
    resetVersion,
    searchAttemptVersion,
    onTrialLimitReached,
    enResolveGroups: activeEnResolveResult?.groups,
  })
  const { modeSwitchSuggestion } = useSidebarModeSuggestion({
    apiClient,
    searchLanguageMode,
    normalizedQuery,
    sentenceQuery,
    isSentenceMode,
    isNumberMode,
    resetVersion,
  })

  const activeCorFormSearchResult = useMemo(() => {
    if (!corFormSearchResult || corFormSearchResult.query !== normalizedQuery) {
      return null
    }
    return corFormSearchResult
  }, [corFormSearchResult, normalizedQuery])

  return {
    searchQuery,
    setSearchQuery,
    searchLanguageMode,
    setSearchLanguageMode,
    normalizedQuery,
    isTrialLimitReached,
    isSentenceMode,
    isNumberMode,
    isMweMode,
    modeSwitchSuggestion,
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    searchApiMatches,
    isWordbankSearchLoading,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorLookupLoading,
    isCorTranslationsLoading,
    sentenceSearchPreviewError,
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  }
}
