import { useMemo, useState } from "react"

import { MobileBottomNav } from "@/app/chrome/sidebar/mobile-bottom-nav"
import { MobileSearchButton } from "@/app/chrome/sidebar/mobile-search-button"
import { MobileSidebarButton } from "@/app/chrome/sidebar/mobile-sidebar-button"
import { SidebarFooterActions } from "@/app/chrome/sidebar/sidebar-footer-actions"
import { SidebarNavigation } from "@/app/chrome/sidebar/sidebar-navigation"
import { useSidebarPageItems } from "@/app/chrome/sidebar/sidebar-page-items"
import { SidebarSearchDialog } from "@/app/chrome/sidebar/sidebar-search-dialog"
import {
  type SidebarSearchResultsActions,
  type SidebarSearchResultsData,
  type SidebarSearchResultsState,
} from "@/app/chrome/sidebar/sidebar-search-results"
import {
  corVariantSelectionValue,
  translatedEnCorVariantSelectionValue,
  useSidebarCommandSelection,
} from "@/app/chrome/sidebar/use-sidebar-command-selection"
import { useSidebarHotkeys } from "@/app/chrome/sidebar/use-sidebar-hotkeys"
import { useSidebarLemmas } from "@/app/chrome/sidebar/use-sidebar-lemmas"
import { useSidebarSearchHistory } from "@/app/chrome/sidebar/use-sidebar-search-history"
import { useSidebarSearch } from "@/app/chrome/sidebar/use-sidebar-search"
import { useSidebarSearchRanking } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { type AppSidebarProps } from "@/app/chrome/sidebar/app-sidebar-types"
import { type WordbankSearchItem } from "@/app/core"
import { Sidebar, SidebarFooter, SidebarHeader, SidebarTrigger, useSidebar } from "@/components/ui/sidebar"

export type { AppSidebarProps } from "@/app/chrome/sidebar/app-sidebar-types"

export function AppSidebar({
  activeSection,
  lemmas,
  sentences,
  wordbankCacheVersion,
  searchTranslationConfigVersion,
  unreadWordbankNotificationCount,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onSelectAccount,
  onOpenWordbankLemma,
  onOpenWordbankLemmaRaw,
  onOpenWordbankMeaning,
  onOpenSentence,
  onAddSentenceToSentencebank,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")
  const { isMobile, setOpenMobile } = useSidebar()

  const closeMobileSidebar = () => { if (isMobile) setOpenMobile(false) }
  const sidebarAction = (action: () => void) => () => {
    action()
    closeMobileSidebar()
  }
  const selectWordbankFromSidebar = sidebarAction(onSelectWordbank)
  const selectSentencebankFromSidebar = sidebarAction(onSelectSentencebank)
  const selectAccountFromSidebar = sidebarAction(onSelectAccount)

  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    isTrialLimitReached,
    isSentenceMode,
    isMweMode,
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    searchApiMatches,
    isWordbankSearchLoading,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorLookupLoading,
    isCorTranslationsLoading,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  } = useSidebarSearch({
    wordbankCacheVersion,
    searchTranslationConfigVersion,
  })
  const searchHistory = useSidebarSearchHistory({
    isSearchOpen,
    onCloseFromHistory: () => {
      setIsSearchOpen(false)
      setTimeout(() => {
        setSearchQuery("")
        setCommandSelectionOverride("")
      }, 200)
    },
  })
  const searchLemmas = useSidebarLemmas(lemmas, isSearchOpen)

  const matchedSavedSentences = useMemo(() => {
    const q = normalizedQuery.toLowerCase().trim()
    if (q.length < 2) return []
    return sentences
      .filter(
        (s) =>
          s.source_text.toLowerCase().includes(q) ||
          (s.english_translation ?? "").toLowerCase().includes(q),
      )
      .slice(0, 6)
  }, [sentences, normalizedQuery])

  const {
    variationCandidateCorIdSet,
    addVariationBySavedResult,
    displayVariantBySavedResult,
    exactSavedVariationKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults,
    hasWordbankActions,
  } = useSidebarSearchRanking({
    lemmas: searchLemmas,
    normalizedQuery,
    searchApiMatches,
    activeCorFormSearchResult,
  })

  const matchingPageItems = useSidebarPageItems({
    normalizedQuery,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
    onOpenWordbankLemma,
  })

  const hasPageResults = matchingPageItems.length > 0
  const hasTranslatedEnResults = activeEnTranslatedCorResults.corSearchVariantsToRender.length > 0
  const hasFallbackEnResults = activeEnTranslatedCorResults.fallbackEnPosGroups.length > 0
  const hasEnResults = hasTranslatedEnResults || hasFallbackEnResults
  const hasMatchedSentences = matchedSavedSentences.length > 0
  const hasAnyResults = isSentenceMode
    ? (Boolean(sentenceSearchPreview) || hasMatchedSentences)
    : (
        hasWordbankSectionResults
        || hasEnResults
        || hasPageResults
        || hasMatchedSentences
        || isWordbankSearchLoading
        || isCorLookupLoading
        || isEnResolveLoading
        || isEnTranslatedCorLoading
      )

  const { commandSelectionValue } = useSidebarCommandSelection({
    activeEnTranslatedCorResults,
    commandSelectionOverride,
    corDidYouMean,
    corSearchVariantsToRender,
    isSearchOpen,
    isSentenceMode,
    matchingPageItems,
    orderedCorSearchGroups,
    orderedWordbankResults,
    sentenceSearchPreview,
    setCommandSelectionOverride,
    wordbankDidYouMean,
  })

  const closeSearch = () => {
    searchHistory.clear()
    setIsSearchOpen(false)
    setTimeout(() => {
      setSearchQuery("")
      setCommandSelectionOverride("")
    }, 200)
  }

  const saveSentenceFromSearch = (sourceText: string, englishTranslation: string | null = null) => {
    closeSearch()
    void onAddSentenceToSentencebank(sourceText, englishTranslation)
  }

  const searchResultState: SidebarSearchResultsState = {
    normalizedQuery,
    isSentenceMode,
    isMweMode,
    hasAnyResults,
    hasWordbankSectionResults,
    hasWordbankActions,
    hasPageResults,
    wordbankDidYouMean,
    corDidYouMean,
  }

  const searchResultData: SidebarSearchResultsData = {
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    matchedSavedSentences,
    orderedWordbankResults,
    displayVariantBySavedResult,
    addVariationBySavedResult,
    exactSavedVariationKeySet,
    orderedCorSearchGroups,
    corSearchVariantsToRender,
    variationCandidateCorIdSet,
    translatedEnCorSearchGroups: activeEnTranslatedCorResults.orderedCorSearchGroups,
    translatedEnCorVariantsToRender: activeEnTranslatedCorResults.corSearchVariantsToRender,
    matchingPageItems,
    isWordbankSearchLoading,
    isCorLookupLoading,
    isCorTranslationsLoading,
    wordbankItemValue: (item: WordbankSearchItem) => `wordbank-${savedWordbankResultKey(item)}`,
    // Sense-discovery fan-out emits one variant per discovered sense, all
    // sharing the same cor_id (since the underlying COR entry's id doesn't
    // differ across senses). Without the meaning_key suffix, cmdk treats them
    // as a single item and hover-highlights every card at once. The shared
    // helpers in use-sidebar-command-selection.ts keep this in sync with the
    // keyboard navigation value list.
    corVariantItemValue: corVariantSelectionValue,
    translatedEnCorVariantItemValue: translatedEnCorVariantSelectionValue,
    enPosGroups: activeEnTranslatedCorResults.fallbackEnPosGroups,
    isEnResolveLoading: isEnResolveLoading,
    isEnTranslatedCorLoading: isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  }

  const searchResultActions: SidebarSearchResultsActions = {
    onAddSentenceFromSearch: async (sourceText: string) => {
      saveSentenceFromSearch(sourceText, sentenceSearchPreview?.english_translation ?? null)
    },
    onSetSearchQuery: (query: string) => { setSearchQuery(query) },
    onOpenWordbankLemma,
    onOpenWordbankLemmaRaw,
    onOpenWordbankMeaning,
    onOpenSentence,
    onAddWordFromSearch,
    onCloseSearch: closeSearch,
  }

  const openSearch = () => {
    searchHistory.push()
    setIsSearchOpen(true)
  }

  useSidebarHotkeys({
    onToggleSearch: () => {
      if (isSearchOpen) closeSearch()
      else openSearch()
    },
    onSelectWordbank,
    onSelectSentencebank,
    onSelectAccount,
  })

  return (
    <>
      {!isMobile && (
        <Sidebar variant="inset" collapsible="icon">
          <SidebarHeader>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="font-brand truncate rounded-sm pl-2 text-left text-[1.25rem] leading-none font-normal tracking-normal not-italic outline-none hover:text-foreground/80 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 group-data-[collapsible=icon]:sr-only"
                onClick={selectWordbankFromSidebar}
              >
                danote
              </button>
              <SidebarTrigger className="ml-auto size-8 cursor-ew-resize group-data-[collapsible=icon]:ml-0 max-md:size-10 max-md:[&_svg:not([class*='size-'])]:size-5" />
            </div>
          </SidebarHeader>
          <SidebarNavigation
            activeSection={activeSection}
            unreadWordbankNotificationCount={unreadWordbankNotificationCount}
            onSelectWordbank={selectWordbankFromSidebar}
            onSelectSentencebank={selectSentencebankFromSidebar}
            onOpenSearch={() => { openSearch(); closeMobileSidebar() }}
          />
          <SidebarFooter>
            <SidebarFooterActions activeSection={activeSection} onSelectAccount={selectAccountFromSidebar} />
          </SidebarFooter>
        </Sidebar>
      )}
      {isMobile && (
        <MobileBottomNav
          activeSection={activeSection}
          onSelectWordbank={onSelectWordbank}
          onSelectSentencebank={onSelectSentencebank}
          onSelectAccount={onSelectAccount}
          onOpenSearch={openSearch}
          unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        />
      )}
      <SidebarSearchDialog
        isOpen={isSearchOpen} commandSelectionValue={commandSelectionValue} searchQuery={searchQuery}
        sentenceSearchPreview={sentenceSearchPreview} isSentenceMode={isSentenceMode}
        isSentenceSearchPreviewLoading={isSentenceSearchPreviewLoading} isTrialLimitReached={isTrialLimitReached}
        searchResultState={searchResultState} searchResultData={searchResultData} searchResultActions={searchResultActions}
        setSearchQuery={setSearchQuery} setCommandSelectionOverride={setCommandSelectionOverride}
        onCloseSearch={closeSearch} onSelectAccount={onSelectAccount} onSaveSentenceFromSearch={saveSentenceFromSearch}
        onOpenChange={(open) => {
          if (open) openSearch()
          else closeSearch()
        }}
      />
      {!isMobile && (
        <>
          <MobileSidebarButton />
          <MobileSearchButton isSearchOpen={isSearchOpen} onOpenSearch={openSearch} />
        </>
      )}
    </>
  )
}
