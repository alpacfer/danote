import { useCallback, useMemo, useState } from "react"

import {
  BACKEND_URL,
  SENTENCE_VERIFY_MAX_CHARS,
  createApiClient,
  normalizeSentenceText,
  hasMultipleWords,
  isShortLetterWord,
  normalizeSearchWord,
} from "@/app/core"
import { searchAttemptKey } from "@/app/chrome/sidebar/sidebar-search-types"
import type { UseSidebarSearchParams } from "@/app/chrome/sidebar/sidebar-search-types"
import { useSidebarCorSearch } from "@/app/chrome/sidebar/use-sidebar-cor-search"
import { useSidebarEnSearch } from "@/app/chrome/sidebar/use-sidebar-en-search"
import { useSidebarSentencePreview } from "@/app/chrome/sidebar/use-sidebar-sentence-preview"
import { useSidebarWordbankSearch } from "@/app/chrome/sidebar/use-sidebar-wordbank-search"
import { numberFromSearchQuery } from "@/app/sections/wordbank/numbers/numbers-data"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

export function useSidebarSearch({
  wordbankCacheVersion,
  searchTranslationConfigVersion,
}: UseSidebarSearchParams) {
  const [searchQuery, setSearchQuery] = useState("")
  const apiClient = useMemo(
    () => createApiClient({ backendUrl: BACKEND_URL, extractErrorMessage }),
    [],
  )
  const resetVersion = `${searchTranslationConfigVersion}:${wordbankCacheVersion}`

  const sentenceQuery = normalizeSentenceText(searchQuery)
  const normalizedQuery = normalizeSearchWord(searchQuery)
  const isNumberMode = numberFromSearchQuery(normalizedQuery) !== null
  const isSentenceMode = !isNumberMode && hasMultipleWords(sentenceQuery) && sentenceQuery.length <= SENTENCE_VERIFY_MAX_CHARS
  const shouldSkipWordLookups = isSentenceMode || isNumberMode
  const isEnglishSingleWordQuery = !isSentenceMode
    && !isNumberMode
    && normalizedQuery.length >= 2
    && !/\s/u.test(normalizedQuery)
    && !isShortLetterWord(normalizedQuery)

  // Banner is keyed to the search attempt that hit the cap, so it clears
  // automatically when the user edits the query (no reset effect needed).
  const [trialLimitedKey, setTrialLimitedKey] = useState<string | null>(null)
  const onTrialLimitReached = useCallback(
    (key: string) => setTrialLimitedKey(key),
    [],
  )
  const isTrialLimitReached = trialLimitedKey === searchAttemptKey(resetVersion, normalizedQuery)

  const { searchApiMatches, wordbankDidYouMean, isWordbankSearchLoading } = useSidebarWordbankSearch({
    apiClient,
    shouldSkipLookup: shouldSkipWordLookups,
    normalizedQuery,
    resetVersion,
  })
  const { corDidYouMean, corFormSearchResult, isCorLookupLoading, isCorTranslationsLoading } = useSidebarCorSearch({
    apiClient,
    shouldSkipLookup: shouldSkipWordLookups,
    normalizedQuery,
    resetVersion,
    onTrialLimitReached,
  })
  const {
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    sentenceSearchPreviewError,
  } = useSidebarSentencePreview({
    apiClient,
    isSentenceMode,
    sentenceQuery,
    resetVersion,
  })
  const {
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  } = useSidebarEnSearch({
    apiClient,
    isEnglishSingleWordQuery,
    isSentenceMode,
    normalizedQuery,
    resetVersion,
    onTrialLimitReached,
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
    normalizedQuery,
    isTrialLimitReached,
    isSentenceMode,
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
