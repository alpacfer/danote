import { useMemo, useState } from "react"

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
import { useSidebarCommandSelection } from "@/app/chrome/sidebar/use-sidebar-command-selection"
import { useSidebarHotkeys } from "@/app/chrome/sidebar/use-sidebar-hotkeys"
import { useSidebarLemmas } from "@/app/chrome/sidebar/use-sidebar-lemmas"
import { useSidebarSearch } from "@/app/chrome/sidebar/use-sidebar-search"
import { useSidebarSearchRanking } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { type AppSection, type CORSearchVariant, type SearchSaveSeed, type SearchFeedbackContext, type SentencebankSentence, type WordbankLemma, type WordbankSearchItem } from "@/app/core"
import { Sidebar, SidebarFooter, SidebarHeader, SidebarTrigger, useSidebar } from "@/components/ui/sidebar"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  sentences: SentencebankSentence[]
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
  unreadWordbankNotificationCount: number
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onSelectAccount: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankLemmaRaw: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onOpenSentence: (id: number) => void
  onAddSentenceToSentencebank: (sourceText: string, englishTranslation?: string | null) => Promise<void>
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
}

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

  useSidebarHotkeys({
    onToggleSearch: () => setIsSearchOpen((current) => !current),
    onSelectWordbank,
    onSelectSentencebank,
    onSelectAccount,
  })

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
    corVariantItemValue: (variant: CORSearchVariant) => `cor-variant-${variant.cor_id}`,
    translatedEnCorVariantItemValue: (variant: CORSearchVariant) => `en-cor-${variant.lemma.toLowerCase()}-${variant.cor_id}`,
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

  const openSearch = () => setIsSearchOpen(true)

  return (
    <>
      <Sidebar variant="inset" collapsible="icon">
        <SidebarHeader>
          <div className="flex h-11 items-end gap-2 pt-1">
            <button
              type="button"
              className="font-brand translate-x-1 -translate-y-1.5 truncate rounded-sm text-left text-[1.25rem] leading-none font-normal tracking-normal not-italic outline-none hover:text-foreground/80 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 group-data-[collapsible=icon]:sr-only"
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
      <SidebarSearchDialog
        isOpen={isSearchOpen} commandSelectionValue={commandSelectionValue} searchQuery={searchQuery}
        sentenceSearchPreview={sentenceSearchPreview} isSentenceMode={isSentenceMode}
        isSentenceSearchPreviewLoading={isSentenceSearchPreviewLoading} isTrialLimitReached={isTrialLimitReached}
        searchResultState={searchResultState} searchResultData={searchResultData} searchResultActions={searchResultActions}
        setSearchQuery={setSearchQuery} setCommandSelectionOverride={setCommandSelectionOverride}
        onCloseSearch={closeSearch} onSelectAccount={onSelectAccount} onSaveSentenceFromSearch={saveSentenceFromSearch}
        onOpenChange={(open) => {
          setIsSearchOpen(open)
          if (!open) {
            setTimeout(() => {
              setSearchQuery("")
              setCommandSelectionOverride("")
            }, 200)
          }
        }}
      />
      <MobileSidebarButton />
      <MobileSearchButton isSearchOpen={isSearchOpen} onOpenSearch={openSearch} />
    </>
  )
}
