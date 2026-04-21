import { useMemo, useState } from "react"

import {
  BACKEND_URL,
  SENTENCE_VERIFY_MAX_CHARS,
  createApiClient,
  normalizeSentenceText,
  hasMultipleWords,
  isShortLetterWord,
  normalizeSearchWord,
} from "@/app/core"
import { detectQueryLanguage, matchingNotesForQuery } from "@/app/chrome/sidebar/sidebar-search-query"
import type { UseSidebarSearchParams } from "@/app/chrome/sidebar/sidebar-search-types"
import { useSidebarCorSearch } from "@/app/chrome/sidebar/use-sidebar-cor-search"
import { useSidebarEnSearch } from "@/app/chrome/sidebar/use-sidebar-en-search"
import { useSidebarSentencePreview } from "@/app/chrome/sidebar/use-sidebar-sentence-preview"
import { useSidebarWordbankSearch } from "@/app/chrome/sidebar/use-sidebar-wordbank-search"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

export function useSidebarSearch({
  savedNotes,
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
  const isSentenceMode = hasMultipleWords(sentenceQuery) && sentenceQuery.length <= SENTENCE_VERIFY_MAX_CHARS
  const isEnglishSingleWordQuery = !isSentenceMode
    && normalizedQuery.length >= 2
    && !/\s/u.test(normalizedQuery)
    && !isShortLetterWord(normalizedQuery)
    && detectQueryLanguage(normalizedQuery) === "en"

  const matchingNotes = useMemo(() => {
    return matchingNotesForQuery(savedNotes, normalizedQuery)
  }, [normalizedQuery, savedNotes])

  const { searchApiMatches, wordbankDidYouMean } = useSidebarWordbankSearch({
    apiClient,
    isSentenceMode,
    normalizedQuery,
    resetVersion,
  })
  const { corDidYouMean, corFormSearchResult, isCorTranslationsLoading } = useSidebarCorSearch({
    apiClient,
    isSentenceMode,
    normalizedQuery,
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
    resetVersion,
  })
  const {
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
  } = useSidebarEnSearch({
    apiClient,
    isEnglishSingleWordQuery,
    isSentenceMode,
    normalizedQuery,
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
    normalizedQuery,
    isSentenceMode,
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
    sentenceSearchPreviewError,
    activeEnResolveResult,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
  }
}
